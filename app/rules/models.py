"""Data models for a RulePreset — the YAML-configurable set of formatting/
structure requirements for one university + work type combination (spec §10).

Administrators create new presets by adding a YAML file under
rules/presets/, without touching Python code.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.common.enums import Alignment, PageOrientation, WorkType


class PageRule(BaseModel):
    size: str = "A4"
    orientation: PageOrientation = PageOrientation.PORTRAIT


class MarginsRule(BaseModel):
    top_mm: float
    bottom_mm: float
    left_mm: float
    right_mm: float
    tolerance_mm: float = 1.0


class FontRule(BaseModel):
    name: str
    size_pt: float
    tolerance_pt: float = 0.5
    allow_headings_bold: bool = True
    max_foreign_font_share_pct: float = 5.0
    """Max % of characters allowed to be in a font other than `name`/`size`
    before it's flagged (small amounts, e.g. formulas/tables, are tolerated)."""


class ParagraphRule(BaseModel):
    alignment: Alignment = Alignment.JUSTIFY
    first_line_indent_cm: float = 1.25
    indent_tolerance_cm: float = 0.15
    line_spacing: float = 1.5
    line_spacing_tolerance: float = 0.1
    max_left_indent_cm: float = 0.5
    max_right_indent_cm: float = 0.5


class HeadingsRule(BaseModel):
    require_numbering: bool = True
    max_level: int = 3
    require_page_break_before_top_level: bool = False


class StructureRule(BaseModel):
    required_sections: list[str] = Field(default_factory=list)
    optional_sections: list[str] = Field(default_factory=list)
    min_words_introduction: int = 250
    min_words_conclusion: int = 200


class ReferencesRule(BaseModel):
    min_sources: int = 15
    require_in_text_citations: bool = True
    max_allowed_duplicate_sources: int = 0


class ScoringWeights(BaseModel):
    formatting: int = 30
    structure: int = 20
    language: int = 15
    style: int = 10
    content: int = 25

    @field_validator("content")
    @classmethod
    def _weights_sum_to_100(cls, v: int, info) -> int:
        # Validated holistically in RulePreset.validate_weights instead, since
        # field_validator only sees fields already parsed at this point.
        return v


class RulePreset(BaseModel):
    id: str
    name: str
    institution: str
    work_type: WorkType
    description: str = ""
    page: PageRule = Field(default_factory=PageRule)
    margins: MarginsRule
    font: FontRule
    paragraph: ParagraphRule = Field(default_factory=ParagraphRule)
    headings: HeadingsRule = Field(default_factory=HeadingsRule)
    structure: StructureRule
    references: ReferencesRule = Field(default_factory=ReferencesRule)
    scoring: ScoringWeights = Field(default_factory=ScoringWeights)
    is_active: bool = True

    def validate_weights(self) -> None:
        total = (
            self.scoring.formatting
            + self.scoring.structure
            + self.scoring.language
            + self.scoring.style
            + self.scoring.content
        )
        if total != 100:
            raise ValueError(
                f"Rule preset '{self.id}': scoring weights must sum to 100, got {total}"
            )
