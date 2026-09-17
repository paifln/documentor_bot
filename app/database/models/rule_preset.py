from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class RulePresetRecord(Base):
    """Optional DB-backed mirror of a RulePreset.

    The current MVP loads presets from YAML files (app/rules/presets/loader.py)
    so non-technical admins can't accidentally corrupt the DB, and so presets
    are versioned in git. This table exists for the planned future admin UI
    (spec §23/§44) where presets get authored via a web form instead of YAML;
    once that ships, PresetRegistry can be pointed at this table instead.
    """

    __tablename__ = "rule_presets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    configuration: Mapped[dict] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
