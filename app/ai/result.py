"""Per-document AI outcome, independent of report rendering and mutable analyzer state."""

from dataclasses import dataclass, field

from app.common.models import Finding

AI_CATEGORIES = ("language", "style", "content")


@dataclass
class AIAnalysisResult:
    findings: list[Finding] = field(default_factory=list)
    category_coverage: dict[str, float] = field(
        default_factory=lambda: dict.fromkeys(AI_CATEGORIES, 0.0)
    )
    failure_reasons: list[str] = field(default_factory=list)
    tokens_used: int = 0

    @property
    def complete(self) -> bool:
        return all(self.category_coverage.get(key, 0) == 1 for key in AI_CATEGORIES)

    @property
    def coverage(self) -> float:
        return sum(self.category_coverage.values()) / len(AI_CATEGORIES)
