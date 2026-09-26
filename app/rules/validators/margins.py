from __future__ import annotations

from app.common.enums import FindingCategory, FindingSource, Severity
from app.common.models import Finding
from app.document.parser import ParsedDocument
from app.i18n import t
from app.rules.models import RulePreset


def validate_margins(
    document: ParsedDocument, preset: RulePreset, lang: str = "ru"
) -> list[Finding]:
    findings: list[Finding] = []
    page = document.page
    rule = preset.margins
    checks = [
        ("left_margin", "label.left_margin", page.margin_left_mm, rule.left_mm),
        ("right_margin", "label.right_margin", page.margin_right_mm, rule.right_mm),
        ("top_margin", "label.top_margin", page.margin_top_mm, rule.top_mm),
        ("bottom_margin", "label.bottom_margin", page.margin_bottom_mm, rule.bottom_mm),
    ]
    for rule_id, label_key, actual, expected in checks:
        label = t(label_key, lang)
        if abs(actual - expected) > rule.tolerance_mm:
            findings.append(
                Finding(
                    category=FindingCategory.FORMATTING,
                    severity=Severity.ERROR,
                    source=FindingSource.RULE_ENGINE,
                    rule_id=f"margins.{rule_id}",
                    location=label,
                    message=t("rule.margin.error", lang, label=label),
                    expected=f"{expected:.0f} мм",
                    actual=f"{actual:.0f} мм",
                )
            )
        else:
            findings.append(
                Finding(
                    category=FindingCategory.FORMATTING,
                    severity=Severity.PASS,
                    source=FindingSource.RULE_ENGINE,
                    rule_id=f"margins.{rule_id}",
                    message=t("rule.margin.pass", lang, label=label),
                )
            )
    return findings
