"""Scoring (spec §17).

Weights come entirely from the RulePreset (admin-configurable), never
hardcoded. The algorithm: each category starts at its max_points and loses
points per finding depending on severity, floored at 0.
"""

from __future__ import annotations

from app.common.enums import FindingCategory, Severity
from app.common.models import CategoryScore, CheckSummary, Finding
from app.rules.models import RulePreset

# Fraction of a category's max points deducted per finding of each severity.
_PENALTY_FRACTIONS: dict[Severity, float] = {
    Severity.CRITICAL: 0.35,
    Severity.ERROR: 0.15,
    Severity.WARNING: 0.05,
    Severity.INFO: 0.0,
    Severity.PASS: 0.0,
}

# Formatting-related categories share the "formatting" scoring bucket, while
# STRUCTURE/LANGUAGE/STYLE/CONTENT map 1:1. References findings count
# towards structure (they concern the required "Список литературы" section).
_CATEGORY_TO_WEIGHT_KEY = {
    FindingCategory.FORMATTING: "formatting",
    FindingCategory.STRUCTURE: "structure",
    FindingCategory.REFERENCES: "structure",
    FindingCategory.LANGUAGE: "language",
    FindingCategory.STYLE: "style",
    FindingCategory.CONTENT: "content",
}


def compute_summary(findings: list[Finding]) -> CheckSummary:
    summary = CheckSummary()
    for f in findings:
        if f.severity == Severity.CRITICAL:
            summary.critical += 1
        elif f.severity == Severity.ERROR:
            summary.errors += 1
        elif f.severity == Severity.WARNING:
            summary.warnings += 1
        elif f.severity == Severity.INFO:
            summary.info += 1
        elif f.severity == Severity.PASS:
            summary.passed += 1
    return summary


def compute_scores(
    findings: list[Finding], preset: RulePreset
) -> tuple[float, list[CategoryScore]]:
    weights = preset.scoring
    max_points = {
        "formatting": float(weights.formatting),
        "structure": float(weights.structure),
        "language": float(weights.language),
        "style": float(weights.style),
        "content": float(weights.content),
    }
    earned = dict(max_points)

    for f in findings:
        weight_key = _CATEGORY_TO_WEIGHT_KEY.get(f.category)
        if weight_key is None:
            continue
        fraction = _PENALTY_FRACTIONS[f.severity]
        if fraction == 0.0:
            continue
        deduction = max_points[weight_key] * fraction
        # AI findings carry a confidence — scale the deduction by it so a
        # low-confidence AI finding costs less than a certain rule-engine one.
        if f.confidence is not None:
            deduction *= f.confidence
        earned[weight_key] = max(0.0, earned[weight_key] - deduction)

    category_scores: list[CategoryScore] = []
    label_map = {
        "formatting": FindingCategory.FORMATTING,
        "structure": FindingCategory.STRUCTURE,
        "language": FindingCategory.LANGUAGE,
        "style": FindingCategory.STYLE,
        "content": FindingCategory.CONTENT,
    }
    for key, category_enum in label_map.items():
        category_scores.append(
            CategoryScore(
                category=category_enum,
                max_points=max_points[key],
                earned_points=round(earned[key], 1),
            )
        )

    total = round(sum(earned.values()), 1)
    return total, category_scores
