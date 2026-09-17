from __future__ import annotations

from app.common.enums import FindingCategory, FindingSource, Severity
from app.common.models import Finding
from app.document.formatting import body_paragraphs
from app.document.parser import ParsedDocument
from app.i18n import t
from app.rules.models import RulePreset


def validate_paragraphs(document: ParsedDocument, preset: RulePreset, lang: str = "ru") -> list[Finding]:
    findings: list[Finding] = []
    rule = preset.paragraph
    body = body_paragraphs(document)

    bad_indent = [p for p in body if abs((p.first_line_indent_cm or 0.0) - rule.first_line_indent_cm) > rule.indent_tolerance_cm]

    if bad_indent:
        first = bad_indent[0]
        actual_val = f"{(first.first_line_indent_cm or 0):.2f} см"
        sample = ", ".join(str(p.index + 1) for p in bad_indent[:10])
        more = f" (+{len(bad_indent) - 10})" if len(bad_indent) > 10 else ""
        findings.append(
            Finding(
                category=FindingCategory.FORMATTING,
                severity=Severity.ERROR,
                source=FindingSource.RULE_ENGINE,
                rule_id="paragraph.first_line_indent",
                location=t("label.paragraphs", lang, list=f"{sample}{more}"),
                message=t("rule.first_line_indent.error", lang),
                expected=f"{rule.first_line_indent_cm:.2f} см",
                actual=actual_val,
            )
        )
    else:
        findings.append(
            Finding(
                category=FindingCategory.FORMATTING,
                severity=Severity.PASS,
                source=FindingSource.RULE_ENGINE,
                rule_id="paragraph.first_line_indent",
                message=t("rule.first_line_indent.pass", lang),
            )
        )

    if rule.alignment.value != "any":
        bad_alignment = [p.index for p in body if p.alignment != rule.alignment.value]
        if bad_alignment:
            sample = ", ".join(str(i + 1) for i in bad_alignment[:10])
            more = f" (+{len(bad_alignment) - 10})" if len(bad_alignment) > 10 else ""
            findings.append(
                Finding(
                    category=FindingCategory.FORMATTING,
                    severity=Severity.WARNING,
                    source=FindingSource.RULE_ENGINE,
                    rule_id="paragraph.alignment",
                    location=t("label.paragraphs", lang, list=f"{sample}{more}"),
                    message=t("rule.alignment.error", lang),
                    expected=rule.alignment.value,
                )
            )
        else:
            findings.append(
                Finding(
                    category=FindingCategory.FORMATTING,
                    severity=Severity.PASS,
                    source=FindingSource.RULE_ENGINE,
                    rule_id="paragraph.alignment",
                    message=t("rule.alignment.pass", lang),
                )
            )

    oversized_indent = [
        p.index
        for p in body
        if (p.left_indent_cm or 0) > rule.max_left_indent_cm
        or (p.right_indent_cm or 0) > rule.max_right_indent_cm
    ]
    if oversized_indent:
        sample = ", ".join(str(i + 1) for i in oversized_indent[:10])
        findings.append(
            Finding(
                category=FindingCategory.FORMATTING,
                severity=Severity.WARNING,
                source=FindingSource.RULE_ENGINE,
                rule_id="paragraph.side_indent",
                location=t("label.paragraphs", lang, list=sample),
                message=t("rule.side_indent", lang),
            )
        )

    return findings
