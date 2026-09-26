"""Strict schemas for LLM output.

We never trust free-form model text. Every AI response is parsed as JSON
and validated against these models; anything that fails validation is
dropped with a warning rather than shown to the user (spec §13/§34).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator

_ALLOWED_CATEGORIES = {"language", "style", "content", "structure"}
_ALLOWED_SEVERITIES = {"critical", "error", "warning", "info"}


class AIError(BaseModel):
    category: str
    severity: str
    location: str = Field(default="", max_length=255)
    original_text: str = ""
    explanation: str = Field(min_length=1, max_length=2000)
    suggestion: str = Field(default="", max_length=2000)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)

    @field_validator("category")
    @classmethod
    def _category_allowed(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in _ALLOWED_CATEGORIES:
            v = "content"
        return v

    @field_validator("severity")
    @classmethod
    def _severity_allowed(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in _ALLOWED_SEVERITIES:
            v = "info"
        return v

    @field_validator("original_text")
    @classmethod
    def _limit_quote_length(cls, v: str) -> str:
        # Keep the quoted excerpt short — this both protects the student's
        # text from being echoed back needlessly and keeps reports concise.
        return v[:200]


class AIErrorList(BaseModel):
    model_config = ConfigDict(extra="forbid")
    errors: list[AIError] = Field(max_length=100)


class IntroductionAnalysis(BaseModel):
    """Structured self-assessment of the introduction's required elements
    (spec §12 'смысловая структура' — relevance, problem, aim, tasks,
    object, subject, methods)."""

    model_config = ConfigDict(extra="forbid")
    has_relevance: StrictBool
    has_problem_statement: StrictBool
    has_aim: StrictBool
    has_tasks: StrictBool
    has_object: StrictBool
    has_subject: StrictBool
    has_methods: StrictBool
    notes: str = Field(default="", max_length=2000)


class ContentAssessment(BaseModel):
    topic_relevance_score: float = Field(ge=0.0, le=1.0, default=0.5)
    logical_coherence_score: float = Field(ge=0.0, le=1.0, default=0.5)
    has_clear_conclusions: StrictBool
    summary: str = ""
