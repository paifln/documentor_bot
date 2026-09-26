"""Data models for a RulePreset — the YAML-configurable set of formatting/
structure requirements for one university + work type combination (spec §10).

Administrators create new presets by adding a YAML file under
rules/presets/, without touching Python code.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from app.common.enums import Alignment, PageOrientation, WorkType


class PageRule(BaseModel):
    size: str = "A4"
    orientation: PageOrientation = PageOrientation.PORTRAIT


class MarginsRule(BaseModel):
    top_mm: float = Field(ge=0)
    bottom_mm: float = Field(ge=0)
    left_mm: float = Field(ge=0)
    right_mm: float = Field(ge=0)
    tolerance_mm: float = Field(default=1.0, ge=0)


class FontRule(BaseModel):
    name: str
    size_pt: float = Field(gt=0)
    tolerance_pt: float = Field(default=0.5, ge=0)
    allow_headings_bold: bool = True
    max_foreign_font_share_pct: float = Field(default=5.0, ge=0, le=100)
    """Max % of characters allowed to be in a font other than `name`/`size`
    before it's flagged (small amounts, e.g. formulas/tables, are tolerated)."""


class ParagraphRule(BaseModel):
    alignment: Alignment = Alignment.JUSTIFY
    first_line_indent_cm: float = Field(default=1.25, ge=0)
    indent_tolerance_cm: float = Field(default=0.15, ge=0)
    line_spacing: float = Field(default=1.5, ge=0)
    line_spacing_tolerance: float = Field(default=0.1, ge=0)
    max_left_indent_cm: float = Field(default=0.5, ge=0)
    max_right_indent_cm: float = Field(default=0.5, ge=0)


class HeadingsRule(BaseModel):
    require_numbering: bool = True
    max_level: int = Field(default=3, ge=1, le=9)
    require_page_break_before_top_level: bool = False


class StructureRule(BaseModel):
    required_sections: list[str] = Field(default_factory=list)
    optional_sections: list[str] = Field(default_factory=list)
    min_words_introduction: int = Field(default=250, ge=0)
    min_words_conclusion: int = Field(default=200, ge=0)

    @field_validator("required_sections", "optional_sections")
    @classmethod
    def valid_sections(cls, values):
        allowed = {
            "introduction",
            "theoretical_part",
            "practical_part",
            "main_body",
            "conclusion",
            "references",
            "appendix",
            "abstract",
            "content_table",
        }
        if len(set(values)) != len(values) or any(value not in allowed for value in values):
            raise ValueError("Sections must use unique canonical keys")
        return values


class ReferencesRule(BaseModel):
    min_sources: int = Field(default=15, ge=0)
    require_in_text_citations: bool = True
    max_allowed_duplicate_sources: int = Field(default=0, ge=0)


class ScoringWeights(BaseModel):
    formatting: int = 30
    structure: int = 20
    language: int = 15
    style: int = 10
    content: int = 25

    @model_validator(mode="after")
    def valid_weights(self):
        values = self.model_dump().values()
        if any(v < 0 for v in values) or sum(values) != 100:
            raise ValueError("Scoring weights must be nonnegative and sum to 100")
        return self


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
