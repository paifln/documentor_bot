from __future__ import annotations

import asyncio
from io import BytesIO

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.messages import answer_long
from app.bot.states import CB, CheckFlowStates
from app.common.exceptions import FileTooLargeError, UnsupportedFormatError
from app.common.utils import sanitize_display_name
from app.config.logging import get_logger
from app.config.settings import get_settings
from app.database.models.user import User
from app.database.repositories.check_repository import CheckRepository
from app.i18n import t
from app.queue import enqueue_check_job
from app.reports.generator import (
    build_errors_message,
    build_recommendations_message,
    build_results_message,
)
from app.rules.presets.loader import get_preset_registry
from app.security.files import SecureFileStore
from app.security.validation import run_all_validations, validate_extension, validate_mime_type
from app.services.checks import restore_result, submit_check

logger = get_logger(__name__)
router = Router(name="document")


@router.message(F.document)
async def handle_document(
    message: Message, state: FSMContext, session: AsyncSession, db_user: User
) -> None:
    settings = get_settings()
    lang = db_user.language or "ru"
    tg_doc = message.document

    data = await state.get_data()
    preset_id = data.get("preset_id") or settings.default_rule_preset

    preset = get_preset_registry().get(preset_id)
    original_name = tg_doc.file_name or "document.docx"
    if not validate_extension(original_name).ok or not validate_mime_type(tg_doc.mime_type).ok:
        raise UnsupportedFormatError()
    if (tg_doc.file_size or 0) > settings.max_file_size_bytes:
        raise FileTooLargeError()
    display_name = sanitize_display_name(original_name)
    size_mb = round((tg_doc.file_size or 0) / (1024 * 1024), 2)
    await message.answer(t("file_received", lang, filename=display_name, size=size_mb))

    class LimitedBuffer(BytesIO):
        def write(self, content):
            if self.tell() + len(content) > settings.max_file_size_bytes:
                raise FileTooLargeError()
            return super().write(content)

    file = await message.bot.get_file(tg_doc.file_id)
    with LimitedBuffer() as destination:
        await message.bot.download_file(file.file_path, destination=destination)
        content = destination.getvalue()
    store = SecureFileStore()
    saved_path = store.save(content, original_name)
    committed = False
    try:
        await asyncio.to_thread(run_all_validations, saved_path, original_name, tg_doc.mime_type)
        progress = await message.answer(t("check_starting", lang))
        payload = dict(
            chat_id=message.chat.id,
            progress_message_id=progress.message_id,
            docx_path=str(saved_path.resolve()),
            display_filename=display_name,
            lang=lang,
            topic=(message.caption or "")[:500],
        )
        check = await submit_check(
            session,
            db_user.id,
            db_user.telegram_id,
            display_name,
            len(content),
            preset,
            payload,
            settings,
        )
        committed = True
        try:
            await enqueue_check_job(check_id=check.id)
        except Exception as exc:
            # The committed outbox row survives Redis outages; periodic dispatch retries.
            logger.warning("enqueue_deferred", check_id=check.id, error_type=type(exc).__name__)
        await state.clear()
        logger.info("check_accepted", check_id=check.id)
    finally:
        if not committed:
            store.delete(saved_path)


@router.message(F.document.is_(None) & (F.content_type != "text"))
async def handle_wrong_content(message: Message, state: FSMContext, db_user: User) -> None:
    current_state = await state.get_state()
    if current_state == CheckFlowStates.waiting_for_document.state:
        await message.answer(t("wrong_content_type", db_user.language or "ru"))


# --- Results menu callbacks (spec §20) ---


@router.callback_query(F.data.startswith(f"{CB.RESULT_SCORES}:"))
async def show_scores(callback: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    check = await _load_check(callback, session, db_user)
    if check is None:
        return
    result = _to_check_result(check)
    await callback.message.answer(build_results_message(result, db_user.language or "ru"))
    await callback.answer()


@router.callback_query(F.data.startswith(f"{CB.RESULT_ERRORS}:"))
async def show_errors(callback: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    check = await _load_check(callback, session, db_user)
    if check is None:
        return
    result = _to_check_result(check)
    await answer_long(callback.message, build_errors_message(result, db_user.language or "ru"))
    await callback.answer()


@router.callback_query(F.data.startswith(f"{CB.RESULT_RECOMMENDATIONS}:"))
async def show_recommendations(
    callback: CallbackQuery, session: AsyncSession, db_user: User
) -> None:
    check = await _load_check(callback, session, db_user)
    if check is None:
        return
    result = _to_check_result(check)
    await answer_long(
        callback.message, build_recommendations_message(result, db_user.language or "ru")
    )
    await callback.answer()


@router.callback_query(F.data.startswith(f"{CB.RESULT_PDF}:"))
async def resend_pdf(callback: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    lang = db_user.language or "ru"
    check = await _load_check(callback, session, db_user)
    if check is None:
        return
    settings = get_settings()
    pdf_path = settings.reports_dir / f"report_{check.id}.pdf"
    if not pdf_path.exists():
        await callback.message.answer(t("pdf_not_available", lang))
        await callback.answer()
        return
    with open(pdf_path, "rb") as f:
        await callback.message.answer_document(
            BufferedInputFile(f.read(), filename=pdf_path.name), caption=t("pdf_caption", lang)
        )
    await callback.answer()


@router.callback_query(F.data == CB.RESULT_NEW_CHECK)
async def new_check_shortcut(callback: CallbackQuery, state: FSMContext, db_user: User) -> None:
    from app.bot.handlers.start import start_check_flow

    await start_check_flow(callback, state, db_user)


async def _load_check(callback: CallbackQuery, session: AsyncSession, db_user: User):
    lang = db_user.language or "ru"
    try:
        check_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer(t("check_not_found", lang))
        return None
    check_repo = CheckRepository(session)
    check = await check_repo.get_for_user(check_id, db_user.telegram_id)
    if check is None:
        await callback.message.answer(t("check_not_found", lang))
        await callback.answer()
        return None
    return check


def _to_check_result(check):
    return restore_result(check)
