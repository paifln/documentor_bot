from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import CheckStatus
from app.database.session import Base, str_enum_column


class Check(Base):
    __tablename__ = "checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    rule_preset_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[CheckStatus] = mapped_column(str_enum_column(CheckStatus), default=CheckStatus.PENDING)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    critical_count: Mapped[int] = mapped_column(default=0)
    error_count: Mapped[int] = mapped_column(default=0)
    warning_count: Mapped[int] = mapped_column(default=0)
    passed_count: Mapped[int] = mapped_column(default=0)
    processing_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_analysis_available: Mapped[bool] = mapped_column(default=True)
    error_detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document: Mapped["Document"] = relationship(back_populates="checks")
    findings: Mapped[list["FindingRecord"]] = relationship(back_populates="check", cascade="all, delete-orphan")
