from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.session import async_session_factory
from app.queue import get_arq_pool

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def readiness() -> dict:
    try:
        async with asyncio.timeout(5):
            async with async_session_factory() as session:
                await session.execute(text("SELECT result_snapshot FROM checks LIMIT 0"))
            pool = await get_arq_pool()
            await pool.ping()
    except Exception:
        raise HTTPException(503, "Dependencies unavailable") from None
    return {"status": "ready"}
