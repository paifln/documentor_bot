from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import authenticated_user, db_session
from app.database.repositories.check_repository import CheckRepository

router = APIRouter(tags=["checks"])


@router.get("/checks/{check_id}")
async def get_check(
    check_id: int,
    session: AsyncSession = Depends(db_session),
    telegram_id: int = Depends(authenticated_user),
) -> dict:
    repo = CheckRepository(session)
    check = await repo.get_for_user(check_id, telegram_id)
    if check is None:
        raise HTTPException(status_code=404, detail="Check not found")

    return {
        "id": check.id,
        "status": check.status.value,
        "score": check.score,
        "result": check.result_snapshot,
        "summary": {
            "critical": check.critical_count,
            "errors": check.error_count,
            "warnings": check.warning_count,
            "passed": check.passed_count,
        },
        "ai_analysis_available": check.ai_analysis_available,
        "findings": [
            {
                "category": f.category.value,
                "severity": f.severity.value,
                "source": f.source.value,
                "location": f.location,
                "message": f.message,
                "expected": f.expected,
                "actual": f.actual,
                "suggestion": f.suggestion,
                "confidence": f.confidence,
            }
            for f in check.findings
        ],
    }
