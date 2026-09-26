from __future__ import annotations

from app.common.enums import FindingCategory, FindingSource, Severity
from app.common.models import Finding
from app.document.formatting import body_paragraphs
from app.document.parser import ParsedDocument
from app.i18n import t
from app.rules.models import RulePreset


def validate_spacing(
    document: ParsedDocument, preset: RulePreset, lang: str = "ru"
) -> list[Finding]:
    findings: list[Finding] = []
    rule = preset.paragraph
    body = body_paragraphs(document)

    mismatched: list[int] = []
    for p in body:
        if p.line_spacing is None or any(
            x in (p.line_spacing_rule or "") for x in ("EXACT", "AT_LEAST")
        ):
            mismatched.append(p.index)
            continue
        if abs(p.line_spacing - rule.line_spacing) > rule.line_spacing_tolerance:
            mismatched.append(p.index)

    if mismatched:
        sample = ", ".join(str(i + 1) for i in mismatched[:10])
        more = f" (+{len(mismatched) - 10})" if len(mismatched) > 10 else ""
        findings.append(
            Finding(
                category=FindingCategory.FORMATTING,
                severity=Severity.ERROR,
                source=FindingSource.RULE_ENGINE,
                rule_id="paragraph.line_spacing",
                location=t("label.paragraphs", lang, list=f"{sample}{more}"),
                message=t("rule.line_spacing.error", lang),
                expected=f"{rule.line_spacing}",
            )
        )
    else:
        findings.append(
            Finding(
                category=FindingCategory.FORMATTING,
                severity=Severity.PASS,
                source=FindingSource.RULE_ENGINE,
                rule_id="paragraph.line_spacing",
                message=t("rule.line_spacing.pass", lang),
            )
        )
    return findings
