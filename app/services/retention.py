"""Retention for source files, reports and persisted excerpts."""

import asyncio
import datetime as dt
import time
from pathlib import Path

from sqlalchemy import delete, select, update

from app.common.enums import CheckStatus
from app.config.settings import get_settings
from app.database.models import Check, Document, FindingRecord
from app.database.session import async_session_factory
from app.security.files import SecureFileStore


def _purge_files(protected):
    settings = get_settings()
    cutoff = time.time() - settings.file_retention_hours * 3600
    for path in settings.storage_dir.glob("cw_*"):
        try:
            if path.resolve() not in protected and path.stat().st_mtime < cutoff:
                SecureFileStore().delete(path)
        except FileNotFoundError:
            continue
    cutoff = time.time() - settings.report_retention_hours * 3600
    for path in settings.reports_dir.glob("report_*.pdf"):
        try:
            if path.is_file() and not path.is_symlink() and path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
        except FileNotFoundError:
            continue


async def _delete_checks(session, ids):
    if not ids:
        return
    document_ids = (await session.scalars(select(Check.document_id).where(Check.id.in_(ids)))).all()
    await session.execute(delete(FindingRecord).where(FindingRecord.check_id.in_(ids)))
    await session.execute(delete(Check).where(Check.id.in_(ids)))
    await session.execute(
        delete(Document).where(Document.id.in_(document_ids), ~Document.checks.any())
    )
    await session.commit()
    settings = get_settings()
    for check_id in ids:
        (settings.reports_dir / f"report_{check_id}.pdf").unlink(missing_ok=True)


async def delete_user_history(telegram_id):
    async with async_session_factory() as session:
        ids = (
            await session.scalars(
                select(Check.id)
                .join(Document)
                .where(
                    Document.user.has(telegram_id=telegram_id),
                    Check.status.in_([CheckStatus.COMPLETED, CheckStatus.FAILED]),
                    Check.delivery_status != "sending",
                )
            )
        ).all()
        await _delete_checks(session, ids)
        return len(ids)


async def purge_retained_data(ctx=None):
    settings = get_settings()
    now = dt.datetime.now(dt.timezone.utc)
    async with async_session_factory() as session:
        await session.execute(
            update(Check)
            .where(
                Check.status == CheckStatus.PENDING,
                Check.created_at < now - dt.timedelta(hours=settings.file_retention_hours),
            )
            .values(
                status=CheckStatus.FAILED, completed_at=now, error_detail="Queue retention expired"
            )
        )
        await session.commit()
        jobs = (
            await session.scalars(
                select(Check.job_payload).where(
                    Check.status.in_([CheckStatus.PENDING, CheckStatus.RUNNING])
                )
            )
        ).all()
        protected = {Path(p["docx_path"]).resolve() for p in jobs if p and "docx_path" in p}
        expired = (
            await session.scalars(
                select(Check.id).where(
                    Check.completed_at < now - dt.timedelta(days=settings.result_retention_days),
                    Check.status.in_([CheckStatus.COMPLETED, CheckStatus.FAILED]),
                    Check.delivery_status != "sending",
                )
            )
        ).all()
        await _delete_checks(session, expired)
    await asyncio.to_thread(_purge_files, protected)
