"""Durable analysis and independent, retryable report delivery.

Only a check ID crosses Redis. Payloads, rule snapshots and results belong to
SQL, so Redis outages or restarts cannot silently discard accepted work.
"""

from __future__ import annotations

import asyncio
import datetime as dt
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile
from arq import cron
from sqlalchemy import update

from app.analysis.pipeline import build_pipeline
from app.bot.keyboards.results import results_keyboard
from app.common.enums import CheckStatus, DocumentStatus
from app.common.exceptions import CourseworkCheckerError
from app.common.models import CheckResult
from app.config.logging import configure_logging, get_logger
from app.config.settings import get_settings
from app.database.models import Check
from app.database.repositories.check_repository import CheckRepository
from app.database.repositories.document_repository import DocumentRepository
from app.database.session import async_session_factory, engine
from app.i18n import t
from app.queue import close_arq_pool
from app.reports.generator import build_summary_message, generate_pdf
from app.rules.models import RulePreset
from app.security.files import SecureFileStore
from app.services.dispatch import dispatch_pending
from app.services.retention import purge_retained_data

logger = get_logger(__name__)

# arq 0.26 constructs the worker before entering its event loop.
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())


async def run_check_job(ctx, *, check_id: int, **legacy) -> None:
    settings = get_settings()
    async with async_session_factory() as session:
        check = await session.get(Check, check_id)
        if (
            check is None
            or check.job_payload is None
            or check.status not in {CheckStatus.PENDING, CheckStatus.COMPLETED}
        ):
            return
        if check.status != CheckStatus.COMPLETED:
            if check.attempts >= settings.max_job_attempts:
                SecureFileStore().delete(Path(check.job_payload["docx_path"]))
                await CheckRepository(session).fail(check, "Analysis retry limit reached")
                await session.commit()
                return
            claimed = await session.execute(
                update(Check)
                .where(Check.id == check_id, Check.status == CheckStatus.PENDING)
                .values(
                    status=CheckStatus.RUNNING,
                    attempts=Check.attempts + 1,
                    started_at=dt.datetime.now(dt.timezone.utc),
                )
            )
            if not claimed.rowcount:
                return
            await session.commit()
        payload = dict(check.job_payload)
        preset = RulePreset.model_validate(check.preset_snapshot)
        snapshot = check.result_snapshot
        document_id = check.document_id
    bot = Bot(token=settings.bot_token)
    lang = payload.get("lang", "ru")
    path = Path(payload["docx_path"])
    pipeline = None
    try:
        if snapshot is None:
            pipeline = build_pipeline(settings)

            async def progress(stage):
                try:
                    await bot.edit_message_text(
                        chat_id=payload["chat_id"],
                        message_id=payload["progress_message_id"],
                        text=t(f"stage.{stage}", lang),
                    )
                except Exception:
                    pass

            result = await pipeline.run(
                path, preset, topic=payload.get("topic", ""), lang=lang, on_progress=progress
            )
            async with async_session_factory() as session:
                check = await session.get(Check, check_id)
                if check is None:
                    return
                await CheckRepository(session).complete(check, result)
                await session.commit()
            snapshot = result.model_dump(mode="json")
        # Delete only after the immutable result is durable; retries use the snapshot.
        SecureFileStore().delete(path)
        async with async_session_factory() as session:
            repo = DocumentRepository(session)
            document = await repo.get(document_id)
            if document is not None and not path.exists():
                await repo.mark_status(document, DocumentStatus.DELETED)
                await session.commit()
        await deliver_result(bot, check_id, CheckResult.model_validate(snapshot), preset, payload)
    except asyncio.CancelledError:
        await reset_attempt(check_id)
        raise
    except Exception as exc:
        logger.error("check_attempt_failed", check_id=check_id, error_type=type(exc).__name__)
        async with async_session_factory() as session:
            check = await session.get(Check, check_id)
            if check is not None and check.status != CheckStatus.COMPLETED:
                if (
                    isinstance(exc, CourseworkCheckerError)
                    or check.attempts >= settings.max_job_attempts
                ):
                    await CheckRepository(session).fail(check, type(exc).__name__)
                    SecureFileStore().delete(path)
                    try:
                        await bot.send_message(
                            chat_id=payload["chat_id"],
                            text=exc.localized_message(lang)
                            if isinstance(exc, CourseworkCheckerError)
                            else t("error.internal", lang),
                        )
                    except Exception:
                        pass
                else:
                    check.status = CheckStatus.PENDING
                await session.commit()
    finally:
        try:
            if pipeline is not None:
                await pipeline.ai_analyzer.provider.aclose()
        finally:
            await bot.session.close()


async def reset_attempt(check_id):
    async with async_session_factory() as session:
        await session.execute(
            update(Check)
            .where(Check.id == check_id, Check.status == CheckStatus.RUNNING)
            .values(status=CheckStatus.PENDING)
        )
        await session.execute(
            update(Check)
            .where(Check.id == check_id, Check.delivery_status == "sending")
            .values(delivery_status="pending")
        )
        await session.commit()


async def deliver_result(bot, check_id, result, preset, payload):
    settings = get_settings()
    async with async_session_factory() as session:
        check = await session.get(Check, check_id)
        if check is None or check.delivery_status != "pending":
            return
        if check.delivery_attempts >= settings.max_job_attempts:
            check.delivery_status = "failed"
            await session.commit()
            return
        claimed = await session.execute(
            update(Check)
            .where(Check.id == check_id, Check.delivery_status == "pending")
            .values(
                delivery_status="sending",
                delivery_attempts=Check.delivery_attempts + 1,
                started_at=dt.datetime.now(dt.timezone.utc),
            )
        )
        if not claimed.rowcount:
            return
        await session.commit()
    lang = payload.get("lang", "ru")
    try:
        pdf = await asyncio.to_thread(
            generate_pdf, result, preset, payload["display_filename"], check_id, lang
        )
        await bot.send_message(
            chat_id=payload["chat_id"],
            text=build_summary_message(result, lang),
            reply_markup=results_keyboard(check_id, lang),
        )
        await bot.send_document(
            chat_id=payload["chat_id"], document=FSInputFile(pdf), caption=t("pdf_caption", lang)
        )
    except asyncio.CancelledError:
        await reset_attempt(check_id)
        raise
    except Exception as exc:
        logger.warning(
            "delivery_failed",
            check_id=check_id,
            error_type=type(exc).__name__,
            cause_type=type(exc.__cause__).__name__ if exc.__cause__ else None,
        )
        async with async_session_factory() as session:
            check = await session.get(Check, check_id)
            if check is not None:
                check.delivery_status = (
                    "failed" if check.delivery_attempts >= settings.max_job_attempts else "pending"
                )
                await session.commit()
                if check.delivery_status == "failed":
                    await update_delivery_progress(bot, payload, "delivery.failed")
    else:
        async with async_session_factory() as session:
            await session.execute(
                update(Check).where(Check.id == check_id).values(delivery_status="sent")
            )
            await session.commit()
        await update_delivery_progress(bot, payload, "delivery.sent")


async def update_delivery_progress(bot, payload, key):
    try:
        await bot.edit_message_text(
            chat_id=payload["chat_id"],
            message_id=payload["progress_message_id"],
            text=t(key, payload.get("lang", "ru")),
        )
    except Exception as exc:
        logger.warning("delivery_progress_failed", error_type=type(exc).__name__)


async def on_startup(ctx):
    configure_logging()
    await dispatch_pending()


async def on_shutdown(ctx):
    await close_arq_pool()
    await engine.dispose()


class WorkerSettings:
    functions = [run_check_job]
    on_startup = on_startup
    on_shutdown = on_shutdown
    from arq.connections import RedisSettings

    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    cron_jobs = [
        cron(dispatch_pending, second={0, 15, 30, 45}, unique=True),
        cron(purge_retained_data, minute={0, 30}, second=5, unique=True),
    ]
    job_timeout = get_settings().job_timeout_seconds
    max_jobs = get_settings().worker_max_jobs
    keep_result = 0
