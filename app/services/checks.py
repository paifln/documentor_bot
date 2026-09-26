"""Transaction boundary for accepting a check; Redis is only a transport.

The check row is the outbox. If enqueue fails after commit, the dispatcher
will rediscover it. A user-row write serializes quota checks on SQLite and
PostgreSQL, avoiding a read-count-then-insert race.
"""

from sqlalchemy import func, select, update

from app.common.enums import CheckStatus, DocumentStatus
from app.common.exceptions import DailyLimitExceededError
from app.common.models import CheckResult, CheckSummary, Finding
from app.database.models import Check, Document, User
from app.database.repositories.check_repository import CheckRepository
from app.database.repositories.document_repository import DocumentRepository


async def submit_check(session, user_id, telegram_id, filename, size, preset, payload, settings):
    await session.execute(update(User).where(User.id == user_id).values(telegram_id=telegram_id))
    repo = CheckRepository(session)
    active = await session.scalar(
        select(func.count(Check.id))
        .join(Document)
        .where(
            Document.user_id == user_id,
            Check.status.in_([CheckStatus.PENDING, CheckStatus.RUNNING]),
        )
    )
    if (
        active >= settings.max_active_checks
        or await repo.count_checks_today(telegram_id) >= settings.max_checks_per_day
    ):
        raise DailyLimitExceededError("Check quota exceeded")
    document = await DocumentRepository(session).create(user_id, filename, size)
    document.status = DocumentStatus.VALIDATED
    check = await repo.create(document.id, preset.id)
    check.preset_snapshot = preset.model_dump(mode="json")
    check.job_payload = payload
    await session.commit()
    return check


def restore_result(check):
    if check.result_snapshot is not None:
        return CheckResult.model_validate(check.result_snapshot)
    # Legacy results have no saved category weights. Never recompute with current YAML.
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
    return CheckResult(
        score=check.score if check.score is not None else 0.0,
        summary=CheckSummary(
            critical=check.critical_count,
            errors=check.error_count,
            warnings=check.warning_count,
            passed=check.passed_count,
        ),
        findings=findings,
        ai_analysis_available=check.ai_analysis_available,
        processing_time_seconds=check.processing_time_seconds,
    )
