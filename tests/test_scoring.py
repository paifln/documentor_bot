from __future__ import annotations

from app.analysis.scoring import compute_scores, compute_summary
from app.common.enums import FindingCategory, FindingSource, Severity
from app.common.models import Finding


def test_no_findings_gives_full_score(sample_preset):
    total, categories = compute_scores([], sample_preset)
    assert total == 100.0
    assert all(c.earned_points == c.max_points for c in categories)


def test_critical_finding_reduces_score(sample_preset):
    findings = [
        Finding(
            category=FindingCategory.STRUCTURE,
            severity=Severity.CRITICAL,
            source=FindingSource.RULE_ENGINE,
            message="Missing section",
        )
    ]
    total, categories = compute_scores(findings, sample_preset)
    assert total < 100.0
    structure_score = next(c for c in categories if c.category == FindingCategory.STRUCTURE)
    assert structure_score.earned_points < structure_score.max_points


def test_ai_confidence_scales_deduction(sample_preset):
    low_conf = Finding(
        category=FindingCategory.STYLE,
        severity=Severity.WARNING,
        source=FindingSource.AI,
        message="maybe an issue",
        confidence=0.1,
    )
    high_conf = Finding(
        category=FindingCategory.STYLE,
        severity=Severity.WARNING,
        source=FindingSource.AI,
        message="definitely an issue",
        confidence=0.95,
    )
    _, low_categories = compute_scores([low_conf], sample_preset)
    _, high_categories = compute_scores([high_conf], sample_preset)

    low_style = next(c for c in low_categories if c.category == FindingCategory.STYLE)
    high_style = next(c for c in high_categories if c.category == FindingCategory.STYLE)
    assert low_style.earned_points > high_style.earned_points


def test_compute_summary_counts_by_severity():
    findings = [
        Finding(category=FindingCategory.FORMATTING, severity=Severity.CRITICAL, source=FindingSource.RULE_ENGINE, message="a"),
        Finding(category=FindingCategory.FORMATTING, severity=Severity.ERROR, source=FindingSource.RULE_ENGINE, message="b"),
        Finding(category=FindingCategory.FORMATTING, severity=Severity.PASS, source=FindingSource.RULE_ENGINE, message="c"),
    ]
    summary = compute_summary(findings)
    assert summary.critical == 1
    assert summary.errors == 1
    assert summary.passed == 1
