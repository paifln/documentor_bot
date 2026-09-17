from __future__ import annotations

import datetime as dt

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import DocumentStatus
from app.database.session import Base, str_enum_column


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    # `filename` is the sanitized DISPLAY name only, never a filesystem path
    # (the real, random on-disk name lives only in SecureFileStore and is
    # not persisted once the file is deleted per the retention policy).
    filename: Mapped[str] = mapped_column(String(255))
    file_size: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[DocumentStatus] = mapped_column(str_enum_column(DocumentStatus), default=DocumentStatus.RECEIVED)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="documents")
    checks: Mapped[list["Check"]] = relationship(back_populates="document")
