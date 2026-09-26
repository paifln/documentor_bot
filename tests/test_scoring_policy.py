from app.analysis.aggregator import aggregate
from app.analysis.scoring import compute_scores
from app.common.enums import FindingCategory, FindingSource, Severity
from app.common.models import Finding


def issue(rule="margins.left", **kwargs):
    return Finding(
        category=FindingCategory.FORMATTING,
        severity=Severity.ERROR,
        source=FindingSource.RULE_ENGINE,
        rule_id=rule,
        message="Mismatch",
        **kwargs,
    )


def test_repeated_sections_do_not_multiply_penalties(sample_preset):
    once = compute_scores([issue()], sample_preset)
    repeated = compute_scores([issue(location=str(n)) for n in range(100)], sample_preset)
    assert once == repeated


def test_overlapping_font_checks_are_one_deduction(sample_preset):
    findings = [issue(rule) for rule in ("font.main", "font.mixed", "font.paragraph_consistency")]
    assert compute_scores(findings, sample_preset) == compute_scores(findings[:1], sample_preset)


def test_score_is_order_independent_and_matches_display(sample_preset):
    findings = [issue("margins.left"), issue("font.main")]
    total, categories = compute_scores(findings, sample_preset)
    assert (total, categories) == compute_scores(findings[::-1], sample_preset)
    assert total == round(sum(c.earned_points for c in categories), 1)


def test_advisory_rule_cannot_reduce_score(sample_preset):
    sample_preset.advisory_rules = ["font.main"]
    assert compute_scores([issue("font.main")], sample_preset)[0] == 100


def test_partial_analysis_excludes_unchecked_categories(sample_preset):
    result = aggregate([], [], sample_preset, {}, False)
    assert result.score == result.max_score == 100
    assert result.scoring_version == "3"
    assert all(not c.evaluated for c in result.category_scores[2:])
