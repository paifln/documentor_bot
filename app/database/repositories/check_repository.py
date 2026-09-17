from __future__ import annotations

import datetime as dt

from sqlalchemy import desc, select
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
        check = Check(document_id=document_id, rule_preset_id=rule_preset_id, status=CheckStatus.RUNNING)
        self.session.add(check)
        await self.session.flush()
        return check

    async def complete(self, check: Check, result: CheckResult) -> Check:
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
                    location=f.location,
                    message=f.message,
                    expected=f.expected,
                    actual=f.actual,
                    suggestion=f.suggestion,
                    confidence=f.confidence,
                )
            )
        await self.session.flush()
        return check

    async def fail(self, check: Check, error_detail: str) -> Check:
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

    async def count_checks_today(self, telegram_id: int) -> int:
        today_start = dt.datetime.now(dt.timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        stmt = (
            select(Check)
            .join(Document, Check.document_id == Document.id)
            .where(Document.user.has(telegram_id=telegram_id))
            .where(Check.created_at >= today_start)
        )
        result = await self.session.execute(stmt)
        return len(result.scalars().all())
