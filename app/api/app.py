"""Minimal FastAPI application.

Not required for the Telegram MVP, but included as the foundation for the
planned web interface / JSON API (spec §44: 'Web interface', 'Экспорт JSON').
Run with: uvicorn app.api.app:app
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import checks, health
from app.database.session import engine
from app.queue import close_arq_pool


@asynccontextmanager
async def lifespan(app):
    yield
    await close_arq_pool()
    await engine.dispose()


app = FastAPI(title="AI CourseWork Checker API", version="0.2.0", lifespan=lifespan)

app.include_router(health.router)
app.include_router(checks.router, prefix="/api/v1")
