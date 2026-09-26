"""Shared result models.

`Finding` is the single currency every part of the pipeline speaks:
rule validators produce them, the AI analyzer produces them (after schema
validation, see app/ai/schemas.py), and the aggregator/report generator
only ever consume this one shape. This keeps explainability (spec §33)
consistent everywhere: every Finding always carries its `source`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.common.enums import FindingCategory, FindingSource, Severity


class Finding(BaseModel):
    category: FindingCategory
    severity: Severity
    source: FindingSource
    rule_id: str | None = None
    location: str = ""
    message: str
    expected: str | None = None
    actual: str | None = None
    suggestion: str | None = None
    original_text: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)  # only set for AI-sourced findings

    def to_display_line(self) -> str:
        line = f"{self.severity.emoji} {self.message}"
        if self.expected and self.actual:
            line += f"\n   Требуется: {self.expected}\n   Обнаружено: {self.actual}"
        if self.suggestion:
            line += f"\n   💡 {self.suggestion}"
        if self.confidence is not None:
            line += f"\n   Уверенность AI: {round(self.confidence * 100)}%"
        return line


class CategoryScore(BaseModel):
    category: FindingCategory
    max_points: float
    earned_points: float
    evaluated: bool = True
    coverage: float = Field(default=1.0, ge=0, le=1)
    deductions: dict[str, float] = Field(default_factory=dict)
    deduction_labels: dict[str, str] = Field(default_factory=dict)

    @property
    def percentage(self) -> float:
        if self.max_points == 0:
            return 100.0
        return round(self.earned_points / self.max_points * 100, 1)


class CheckSummary(BaseModel):
    critical: int = 0
    errors: int = 0
    warnings: int = 0
    passed: int = 0
    info: int = 0


class CheckResult(BaseModel):
    """The single unified result object described in spec §43."""

    score: float
    max_score: float = 100.0
    summary: CheckSummary
    category_scores: list[CategoryScore] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    structure_sections_found: dict[str, bool] = Field(default_factory=dict)
    ai_analysis_available: bool = True
    ai_coverage: float = 0.0
    ai_tokens_used: int = 0
    scoring_version: str = "legacy"
    preset_status: str = "unverified"
    provisional: bool = False
    evaluated_max_score: float = 100.0
    ai_failure_reasons: list[str] = Field(default_factory=list)
    processing_time_seconds: float | None = None
