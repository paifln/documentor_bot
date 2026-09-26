from __future__ import annotations

from app.common.enums import FindingCategory, FindingSource, Severity
from app.common.models import Finding
from app.document.parser import ParsedDocument
from app.document.structure import StructureReport
from app.i18n import t
from app.rules.models import RulePreset


def validate_headings(
    document: ParsedDocument, structure: StructureReport, preset: RulePreset, lang: str = "ru"
) -> list[Finding]:
    findings: list[Finding] = []
    rule = preset.headings

    too_deep = [h for h in structure.headings if h.level > rule.max_level]
    if too_deep:
        findings.append(
            Finding(
                category=FindingCategory.FORMATTING,
                severity=Severity.WARNING,
                source=FindingSource.RULE_ENGINE,
                rule_id="headings.max_level",
                location=", ".join(h.raw_text[:40] for h in too_deep[:5]),
                message=t("rule.heading.too_deep", lang, max_level=rule.max_level),
            )
        )

    # Numbering convention in Russian/Kazakh academic writing: only
    # substantive chapters get numbers ("1 Теоретическая часть", "2
    # Практическая часть"). Введение/Заключение/Список литературы/
    # Приложение are conventionally LEFT UNNUMBERED — checking them here
    # would flag essentially every correctly-formatted document.
    _CONVENTIONALLY_UNNUMBERED = {
        "introduction",
        "conclusion",
        "references",
        "abstract",
        "appendix",
        "content_table",
    }

    if rule.require_numbering:
        unnumbered = [
            h
            for h in structure.headings
            if h.level <= 2 and not h.numbering and h.section_key not in _CONVENTIONALLY_UNNUMBERED
        ]
        if unnumbered:
            sample = ", ".join(f"«{h.raw_text[:30]}»" for h in unnumbered[:5])
            findings.append(
                Finding(
                    category=FindingCategory.FORMATTING,
                    severity=Severity.WARNING,
                    source=FindingSource.RULE_ENGINE,
                    rule_id="headings.numbering_required",
                    location=sample,
                    message=t("rule.heading.unnumbered", lang),
                )
            )

    if not structure.headings:
        findings.append(
            Finding(
                category=FindingCategory.STRUCTURE,
                severity=Severity.CRITICAL,
                source=FindingSource.RULE_ENGINE,
                rule_id="headings.none_found",
                message=t("rule.heading.none_found", lang),
                suggestion=t("rule.heading.none_found.suggestion", lang),
            )
        )
    else:
        findings.append(
            Finding(
                category=FindingCategory.STRUCTURE,
                severity=Severity.PASS,
                source=FindingSource.RULE_ENGINE,
                rule_id="headings.found",
                message=t("rule.heading.found", lang, n=len(structure.headings)),
            )
        )

    return findings
