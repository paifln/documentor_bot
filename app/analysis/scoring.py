"""Scoring (spec §17).

Weights come entirely from the RulePreset (admin-configurable), never
hardcoded. The algorithm: each category starts at its max_points and loses
points per distinct criterion depending on severity, floored at 0.
Repeated observations and overlapping font checks are charged only once.
This is a diagnostic index, not an academic grade.
"""

from __future__ import annotations

from app.common.enums import FindingCategory, FindingSource, Severity
from app.common.models import CategoryScore, CheckSummary, Finding
from app.rules.models import RulePreset

# Several validators describe the same underlying defect. Charge it once.
_RULE_GROUPS = {
    "font.main": "font",
    "font.mixed": "font",
    "font.paragraph_consistency": "font",
    "font.name": "font",
    "references.missing": "structure.section.references",
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

    # One maximum penalty per criterion, irrespective of document length,
    # duplicate AI responses or how many OOXML sections repeat a defect.
    penalties: dict[str, dict[str, float]] = {key: {} for key in max_points}
    labels: dict[str, dict[str, str]] = {key: {} for key in max_points}
    fractions = {
        Severity.CRITICAL: preset.scoring_policy.critical,
        Severity.ERROR: preset.scoring_policy.error,
        Severity.WARNING: preset.scoring_policy.warning,
    }
    for f in findings:
        weight_key = _CATEGORY_TO_WEIGHT_KEY.get(f.category)
        if weight_key is None or f.rule_id in preset.advisory_rules:
            continue
        fraction = fractions.get(f.severity, 0.0)
        if not fraction:
            continue
        if f.source == FindingSource.AI and f.confidence is not None:
            fraction *= f.confidence
        criterion = _RULE_GROUPS.get(f.rule_id, f.rule_id) or f.message.strip().casefold()
        criterion = f"{f.source.value}:{criterion}"
        previous = penalties[weight_key].get(criterion, 0.0)
        if fraction > previous or (
            fraction == previous and f.message < labels[weight_key].get(criterion, f.message)
        ):
            labels[weight_key][criterion] = f.message
        penalties[weight_key][criterion] = max(penalties[weight_key].get(criterion, 0.0), fraction)
    for key in earned:
        earned[key] = max_points[key] * max(0.0, 1 - sum(penalties[key].values()))

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
                deductions={
                    k: round(v * max_points[key], 2) for k, v in sorted(penalties[key].items())
                },
                deduction_labels=labels[key],
            )
        )

    total = round(sum(c.earned_points for c in category_scores), 1)
    return total, category_scores
