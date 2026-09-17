from __future__ import annotations

from app.common.enums import FindingCategory, FindingSource, Severity
from app.common.models import Finding
from app.document.parser import ParsedDocument
from app.i18n import t
from app.rules.models import RulePreset

_A4 = (210.0, 297.0)
_SIZE_TOLERANCE_MM = 3.0


def validate_page(document: ParsedDocument, preset: RulePreset, lang: str = "ru") -> list[Finding]:
    findings: list[Finding] = []
    page = document.page

    if preset.page.size.upper() == "A4":
        w, h = sorted([page.page_width_mm, page.page_height_mm])
        expected_w, expected_h = sorted(_A4)
        if abs(w - expected_w) > _SIZE_TOLERANCE_MM or abs(h - expected_h) > _SIZE_TOLERANCE_MM:
            findings.append(
                Finding(
                    category=FindingCategory.FORMATTING,
                    severity=Severity.ERROR,
                    source=FindingSource.RULE_ENGINE,
                    rule_id="page.size",
                    location=t("label.page_params", lang),
                    message=t("rule.page_size.error", lang),
                    expected="A4 (210 × 297 мм)",
                    actual=f"{page.page_width_mm:.0f} × {page.page_height_mm:.0f} мм",
                )
            )
        else:
            findings.append(_pass("page.size", t("rule.page_size.pass", lang)))

    actual_orientation = page.orientation
    if actual_orientation != preset.page.orientation.value:
        findings.append(
            Finding(
                category=FindingCategory.FORMATTING,
                severity=Severity.ERROR,
                source=FindingSource.RULE_ENGINE,
                rule_id="page.orientation",
                location=t("label.page_params", lang),
                message=t("rule.orientation.error", lang),
                expected=preset.page.orientation.value,
                actual=actual_orientation,
            )
        )
    else:
        findings.append(_pass("page.orientation", t("rule.orientation.pass", lang)))

    return findings


def validate_headers_footers(document: ParsedDocument, preset: RulePreset, lang: str = "ru") -> list[Finding]:
    """Informational only — the spec doesn't mandate a specific header/footer
    policy per preset by default, but we surface presence for transparency."""
    findings: list[Finding] = []
    present = document.has_header or document.has_footer
    findings.append(
        Finding(
            category=FindingCategory.FORMATTING,
            severity=Severity.INFO,
            source=FindingSource.RULE_ENGINE,
            rule_id="page.header_footer",
            location=t("label.headers_footers", lang),
            message=t("rule.header_footer.present" if present else "rule.header_footer.absent", lang),
        )
    )
    return findings


def _pass(rule_id: str, message: str) -> Finding:
    return Finding(
        category=FindingCategory.FORMATTING,
        severity=Severity.PASS,
        source=FindingSource.RULE_ENGINE,
        rule_id=rule_id,
        message=message,
    )
