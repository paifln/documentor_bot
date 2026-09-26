"""Recover and dispatch durable checks. Safe to run in bot and worker processes."""

import asyncio
import datetime as dt

from sqlalchemy import and_, or_, select, update

from app.common.enums import CheckStatus
from app.config.logging import get_logger
from app.config.settings import get_settings
from app.database.models import Check
from app.database.session import async_session_factory
from app.queue import enqueue_check_job

logger = get_logger(__name__)


async def dispatch_pending(ctx=None):
    settings = get_settings()
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(
        seconds=settings.job_timeout_seconds + 60
    )
    async with async_session_factory() as session:
        await session.execute(
            update(Check)
            .where(Check.status == CheckStatus.RUNNING, Check.started_at < cutoff)
            .values(status=CheckStatus.PENDING)
        )
        await session.execute(
            update(Check)
            .where(
                Check.status == CheckStatus.COMPLETED,
                Check.delivery_status == "sending",
                Check.started_at < cutoff,
            )
            .values(delivery_status="pending")
        )
        await session.commit()
        ids = (
            await session.scalars(
                select(Check.id)
                .where(
                    Check.job_payload.is_not(None),
                    or_(
                        Check.status == CheckStatus.PENDING,
                        and_(
                            Check.status == CheckStatus.COMPLETED,
                            Check.delivery_status == "pending",
                        ),
                    ),
                )
                .order_by(Check.id)
                .limit(100)
            )
        ).all()
    for check_id in ids:
        await enqueue_check_job(check_id=check_id)


async def dispatch_loop():
    while True:
        try:
            await dispatch_pending()
        except Exception as exc:
            logger.warning("dispatch_failed", error_type=type(exc).__name__)
        await asyncio.sleep(15)
