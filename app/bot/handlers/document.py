from __future__ import annotations

from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.states import CB, CheckFlowStates
from app.common.exceptions import DailyLimitExceededError
from app.common.utils import sanitize_display_name
from app.config.logging import get_logger
from app.config.settings import get_settings
from app.database.models.user import User
from app.database.repositories.check_repository import CheckRepository
from app.database.repositories.document_repository import DocumentRepository
from app.i18n import t
from app.queue import enqueue_check_job
from app.reports.generator import (
    build_errors_message,
    build_recommendations_message,
    build_results_message,
    generate_pdf,
)
from app.rules.presets.loader import get_preset_registry
from app.security.files import SecureFileStore
from app.security.validation import run_all_validations

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

    check_repo = CheckRepository(session)
    checks_today = await check_repo.count_checks_today(db_user.telegram_id)
    if checks_today >= settings.max_checks_per_day:
        raise DailyLimitExceededError(f"user {db_user.telegram_id} hit daily limit")

    display_name = sanitize_display_name(tg_doc.file_name or "document.docx")
    size_mb = round((tg_doc.file_size or 0) / (1024 * 1024), 2)

    await message.answer(t("file_received", lang, filename=display_name, size=size_mb))

    file = await message.bot.get_file(tg_doc.file_id)
    file_bytes = await message.bot.download_file(file.file_path)
    content = file_bytes.read()

    store = SecureFileStore()
    saved_path: Path = store.save(content, display_name)

    try:
        run_all_validations(saved_path, display_name, tg_doc.mime_type)
    except Exception:
        store.delete(saved_path)
        raise

    doc_repo = DocumentRepository(session)
    document = await doc_repo.create(user_id=db_user.id, filename=display_name, file_size=len(content))
    check = await check_repo.create(document_id=document.id, rule_preset_id=preset_id)
    await session.commit()

    progress_message = await message.answer(t("check_starting", lang))

    await enqueue_check_job(
        telegram_id=db_user.telegram_id,
        chat_id=message.chat.id,
        progress_message_id=progress_message.message_id,
        document_id=document.id,
        check_id=check.id,
        docx_path=str(saved_path),
        preset_id=preset_id,
        display_filename=display_name,
        lang=lang,
    )

    await state.clear()
    logger.info("check_enqueued", check_id=check.id, preset_id=preset_id, lang=lang)


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
    await callback.message.answer(build_errors_message(result, db_user.language or "ru"))
    await callback.answer()


@router.callback_query(F.data.startswith(f"{CB.RESULT_RECOMMENDATIONS}:"))
async def show_recommendations(callback: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    check = await _load_check(callback, session, db_user)
    if check is None:
        return
    result = _to_check_result(check)
    await callback.message.answer(build_recommendations_message(result, db_user.language or "ru"))
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
    check_id = int(callback.data.split(":", 1)[1])
    check_repo = CheckRepository(session)
    check = await check_repo.get_with_findings(check_id)
    if check is None:
        await callback.message.answer(t("check_not_found", lang))
        await callback.answer()
        return None
    return check


def _to_check_result(check):
    """Rebuild a lightweight CheckResult-like view from persisted rows for
    the results-menu callbacks (avoids re-running analysis)."""
    from app.common.models import CategoryScore, CheckResult, CheckSummary, Finding

    findings = [
        Finding(
            category=f.category,
            severity=f.severity,
            source=f.source,
            rule_id=f.rule_id,
            location=f.location,
            message=f.message,
            expected=f.expected,
            actual=f.actual,
            suggestion=f.suggestion,
            confidence=f.confidence,
        )
        for f in check.findings
    ]

    from app.analysis.scoring import compute_scores
    from app.rules.presets.loader import get_preset_registry

    try:
        preset = get_preset_registry().get(check.rule_preset_id)
    except Exception:  # noqa: BLE001 - preset may have been removed/renamed since the check ran
        weights = {"formatting": 30, "structure": 20, "language": 15, "style": 10, "content": 25}

        class _FakeScoring:
            def __init__(self, w):
                for k, v in w.items():
                    setattr(self, k, v)

        class _FakePreset:
            scoring = _FakeScoring(weights)

        preset = _FakePreset()

    total, category_scores = compute_scores(findings, preset)

    summary = CheckSummary(
        critical=check.critical_count,
        errors=check.error_count,
        warnings=check.warning_count,
        passed=check.passed_count,
    )

    return CheckResult(
        score=check.score or total,
        summary=summary,
        category_scores=category_scores,
        findings=findings,
        ai_analysis_available=check.ai_analysis_available,
        processing_time_seconds=check.processing_time_seconds,
    )
