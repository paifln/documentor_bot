"""Background worker (spec §36).

Architecture:
    Telegram -> Bot (aiogram) -> enqueue_check_job() -> Redis -> Worker (this file)
                                                                    |
                                                                    v
                                                    DOCX parser -> Rule Engine -> AI -> PDF -> Bot.send_message

Running: `arq app.worker.WorkerSettings` (see docker-compose.yml `worker` service).
The worker owns a *separate* short-lived aiogram Bot instance so it can push
progress updates and the final report directly to the user's chat without
going through the polling/webhook process.

Everything user-visible here is rendered via app.i18n.t(key, lang) using
the `lang` the bot handler captured from the user at enqueue time (spec:
язык интерфейса — kk/ru/en).
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from aiogram import Bot
from aiogram.types import BufferedInputFile

from app.analysis.pipeline import build_pipeline
from app.bot.keyboards.results import results_keyboard
from app.common.enums import DocumentStatus
from app.common.exceptions import CourseworkCheckerError
from app.config.logging import configure_logging, get_logger

# --- Defensive fix for a known arq/uvloop incompatibility ---
# If uvloop happens to be installed (it gets pulled in transitively by some
# dependency extras, e.g. `uvicorn[standard]`), arq auto-adopts it as the
# global asyncio event loop policy. Recent uvloop releases (>=0.20) removed
# the "silently create a loop if none exists" fallback from
# get_event_loop(), but arq's own Worker.__init__ still calls the old-style
# `asyncio.get_event_loop()` *before* any loop is running — which then
# raises `RuntimeError: There is no current event loop in thread
# 'MainThread'` and crashes the worker on startup. Explicitly creating and
# registering a loop here, before arq's CLI builds the Worker, sidesteps
# the incompatibility regardless of which event loop policy ends up active.
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())
from app.config.settings import get_settings
from app.database.repositories.check_repository import CheckRepository
from app.database.repositories.document_repository import DocumentRepository
from app.database.session import async_session_factory
from app.i18n import normalize_lang, t
from app.reports.generator import build_summary_message, generate_pdf
from app.rules.presets.loader import get_preset_registry
from app.security.files import SecureFileStore

logger = get_logger(__name__)

_STAGE_KEYS = {
    "structure": "stage.structure",
    "formatting": "stage.formatting",
    "text": "stage.text",
    "ai": "stage.ai",
    "report": "stage.report",
}


async def run_check_job(
    ctx,
    *,
    telegram_id: int,
    chat_id: int,
    progress_message_id: int,
    document_id: int,
    check_id: int,
    docx_path: str,
    preset_id: str,
    display_filename: str,
    lang: str = "ru",
) -> None:
    lang = normalize_lang(lang)
    settings = get_settings()
    bot = Bot(token=settings.bot_token)
    store = SecureFileStore()
    started = time.monotonic()

    async def on_progress(stage: str) -> None:
        key = _STAGE_KEYS.get(stage)
        if not key:
            return
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=progress_message_id, text=t(key, lang))
        except Exception:  # noqa: BLE001 - message may be identical / already edited
            pass

    try:
        preset = get_preset_registry().get(preset_id)
        pipeline = build_pipeline(settings)

        result = await pipeline.run(
            docx_path=Path(docx_path),
            preset=preset,
            lang=lang,
            on_progress=on_progress,
        )

        async with async_session_factory() as session:
            check_repo = CheckRepository(session)
            doc_repo = DocumentRepository(session)

            check = await check_repo.get_with_findings(check_id)
            if check is None:
                logger.error("check_not_found_in_worker", check_id=check_id)
                return
            await check_repo.complete(check, result)

            document = await doc_repo.get(document_id)
            if document:
                await doc_repo.mark_status(document, DocumentStatus.DELETED)

            await session.commit()

        pdf_path = generate_pdf(result, preset, display_filename, check_id, lang)

        summary_text = build_summary_message(result, lang)
        await bot.send_message(
            chat_id=chat_id,
            text=summary_text,
            reply_markup=results_keyboard(check_id, lang),
        )
        with open(pdf_path, "rb") as f:
            await bot.send_document(
                chat_id=chat_id,
                document=BufferedInputFile(f.read(), filename=f"report_{check_id}.pdf"),
                caption=t("pdf_caption", lang),
            )

        logger.info(
            "check_job_completed",
            check_id=check_id,
            score=result.score,
            elapsed=round(time.monotonic() - started, 2),
        )

    except CourseworkCheckerError as exc:
        logger.error("check_job_failed_known", check_id=check_id, error=exc.detail)
        await _fail_check(check_id, exc.detail)
        await bot.send_message(chat_id=chat_id, text=exc.localized_message(lang))
    except Exception as exc:  # noqa: BLE001
        logger.error("check_job_failed_unknown", check_id=check_id, error=str(exc))
        await _fail_check(check_id, str(exc))
        await bot.send_message(chat_id=chat_id, text=t("error.internal", lang))
    finally:
        store.delete(Path(docx_path))
        await bot.session.close()


async def _fail_check(check_id: int, error_detail: str) -> None:
    async with async_session_factory() as session:
        check_repo = CheckRepository(session)
        check = await check_repo.get_with_findings(check_id)
        if check:
            await check_repo.fail(check, error_detail)
            await session.commit()


async def _on_startup(ctx) -> None:
    configure_logging()
    logger.info("worker_started")


async def _on_shutdown(ctx) -> None:
    logger.info("worker_shutdown")


def _redis_settings():
    from arq.connections import RedisSettings

    return RedisSettings.from_dsn(get_settings().redis_url)


class WorkerSettings:
    functions = [run_check_job]
    on_startup = _on_startup
    on_shutdown = _on_shutdown
    redis_settings = _redis_settings()
