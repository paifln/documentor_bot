from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import FindingCategory, FindingSource, Severity
from app.database.session import Base, str_enum_column

if TYPE_CHECKING:
    from app.database.models.check import Check


class FindingRecord(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    check_id: Mapped[int] = mapped_column(ForeignKey("checks.id"), index=True)
    category: Mapped[FindingCategory] = mapped_column(str_enum_column(FindingCategory))
    severity: Mapped[Severity] = mapped_column(str_enum_column(Severity))
    source: Mapped[FindingSource] = mapped_column(str_enum_column(FindingSource))
    rule_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    location: Mapped[str] = mapped_column(String(255), default="")
    message: Mapped[str] = mapped_column(Text)
    expected: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actual: Mapped[str | None] = mapped_column(String(255), nullable=True)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    check: Mapped["Check"] = relationship(back_populates="findings")
