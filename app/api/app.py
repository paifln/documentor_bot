"""Minimal FastAPI application.

Not required for the Telegram MVP, but included as the foundation for the
planned web interface / JSON API (spec §44: 'Web interface', 'Экспорт JSON').
Run with: uvicorn app.api.app:app
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import checks, health

app = FastAPI(title="AI CourseWork Checker API", version="0.1.0")

app.include_router(health.router)
app.include_router(checks.router, prefix="/api/v1")
