"""Merges Rule Engine + AI findings into the single unified result object
described in spec §43."""

from __future__ import annotations

from app.analysis.scoring import compute_scores, compute_summary
from app.common.models import CheckResult, Finding
from app.rules.models import RulePreset

_SEVERITY_ORDER = {"critical": 0, "error": 1, "warning": 2, "info": 3, "pass": 4}


def aggregate(
    rule_findings: list[Finding],
    ai_findings: list[Finding],
    preset: RulePreset,
    sections_found: dict[str, bool],
    ai_available: bool,
    processing_time_seconds: float | None = None,
) -> CheckResult:
    all_findings = [*rule_findings, *ai_findings]
    all_findings.sort(key=lambda f: _SEVERITY_ORDER.get(f.severity.value, 9))

    total, category_scores = compute_scores(all_findings, preset)
    if not ai_available:
        for category in category_scores:
            if category.category.value in {"language", "style", "content"}:
                category.evaluated = False
                category.earned_points = 0.0
        total = round(sum(c.earned_points for c in category_scores if c.evaluated), 1)
    maximum = sum(c.max_points for c in category_scores if c.evaluated)
    summary = compute_summary(all_findings)

    return CheckResult(
        score=total,
        max_score=maximum,
        summary=summary,
        category_scores=category_scores,
        findings=all_findings,
        structure_sections_found=sections_found,
        ai_analysis_available=ai_available,
        processing_time_seconds=processing_time_seconds,
    )
