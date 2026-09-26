from __future__ import annotations

import datetime as dt

from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums import CheckStatus
from app.common.models import CheckResult
from app.database.models.check import Check
from app.database.models.document import Document
from app.database.models.finding import FindingRecord


class CheckRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, document_id: int, rule_preset_id: str) -> Check:
        check = Check(
            document_id=document_id, rule_preset_id=rule_preset_id, status=CheckStatus.PENDING
        )
        self.session.add(check)
        await self.session.flush()
        return check

    async def complete(self, check: Check, result: CheckResult) -> Check:
        await self.session.execute(delete(FindingRecord).where(FindingRecord.check_id == check.id))
        check.result_snapshot = result.model_dump(mode="json")
        check.status = CheckStatus.COMPLETED
        check.score = result.score
        check.critical_count = result.summary.critical
        check.error_count = result.summary.errors
        check.warning_count = result.summary.warnings
        check.passed_count = result.summary.passed
        check.processing_time_seconds = result.processing_time_seconds
        check.ai_analysis_available = result.ai_analysis_available
        check.completed_at = dt.datetime.now(dt.timezone.utc)

        for f in result.findings:
            self.session.add(
                FindingRecord(
                    check_id=check.id,
                    category=f.category,
                    severity=f.severity,
                    source=f.source,
                    rule_id=f.rule_id,
                    location=f.location[:255],
                    message=f.message,
                    expected=f.expected[:255] if f.expected is not None else None,
                    actual=f.actual[:255] if f.actual is not None else None,
                    suggestion=f.suggestion,
                    confidence=f.confidence,
                )
            )
        await self.session.flush()
        return check

    async def fail(self, check: Check, error_detail: str) -> Check:
        if check.status == CheckStatus.COMPLETED:
            return check
        check.status = CheckStatus.FAILED
        check.error_detail = error_detail[:500]
        check.completed_at = dt.datetime.now(dt.timezone.utc)
        await self.session.flush()
        return check

    async def history_for_user(self, telegram_id: int, limit: int = 10) -> list[Check]:
        stmt = (
            select(Check)
            .join(Document, Check.document_id == Document.id)
            .join(Document.user)
            .where(Document.user.has(telegram_id=telegram_id))
            .order_by(desc(Check.created_at))
            .limit(limit)
            .options(selectinload(Check.document))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_with_findings(self, check_id: int) -> Check | None:
        stmt = select(Check).where(Check.id == check_id).options(selectinload(Check.findings))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_for_user(self, check_id: int, telegram_id: int) -> Check | None:
        stmt = (
            select(Check)
            .join(Document)
            .where(Check.id == check_id, Document.user.has(telegram_id=telegram_id))
            .options(selectinload(Check.findings))
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def count_checks_today(self, telegram_id: int) -> int:
        today_start = dt.datetime.now(dt.timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        stmt = (
            select(func.count(Check.id))
            .join(Document, Check.document_id == Document.id)
            .where(Document.user.has(telegram_id=telegram_id))
            .where(Check.created_at >= today_start)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
