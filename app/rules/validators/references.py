"""Reference-list checks (spec §15).

IMPORTANT: this module only checks *counting and pattern* properties
(source count, duplicate entries, presence of in-text citation markers).
It never claims a cited source actually exists — that would require an
external bibliographic database this system does not have access to.
"""

from __future__ import annotations

import re

from app.common.enums import FindingCategory, FindingSource, Severity
from app.common.models import Finding
from app.document.structure import StructureReport
from app.i18n import t
from app.rules.models import RulePreset

_IN_TEXT_CITATION = re.compile(r"\[\s*\d+(\s*[,\-]\s*\d+)*\s*\]")
_ENTRY_NUMBER_PREFIX = re.compile(r"^\s*\d+[.\)]\s*")
_REFERENCES_HEADING_PREFIX = re.compile(r"(?i)^(список|references|bibliography|әдебиеттер)\s")


def _split_reference_entries(section_text: str) -> list[str]:
    lines = [ln.strip() for ln in section_text.split("\n") if ln.strip()]
    entries = [ln for ln in lines if _ENTRY_NUMBER_PREFIX.match(ln) or len(ln) > 15]
    return entries


def validate_references(
    references_section_text: str, structure: StructureReport, preset: RulePreset, lang: str = "ru"
) -> list[Finding]:
    findings: list[Finding] = []
    rule = preset.references

    ref_heading = structure.detected_sections.get("references")
    if ref_heading is None:
        findings.append(
            Finding(
                category=FindingCategory.REFERENCES,
                severity=Severity.CRITICAL,
                source=FindingSource.RULE_ENGINE,
                rule_id="references.missing",
                message=t("rule.references.missing", lang),
            )
        )
        return findings

    content = "\n".join(
        line
        for line in references_section_text.splitlines()
        if line.strip() != ref_heading.raw_text.strip()
    )
    entries = _split_reference_entries(content)
    entries = [e for e in entries if not _REFERENCES_HEADING_PREFIX.match(e)]

    count = len(entries)
    if count < rule.min_sources:
        findings.append(
            Finding(
                category=FindingCategory.REFERENCES,
                severity=Severity.ERROR,
                source=FindingSource.RULE_ENGINE,
                rule_id="references.min_count",
                message=t("rule.references.min_count", lang),
                expected=f">= {rule.min_sources}",
                actual=str(count),
            )
        )
    else:
        findings.append(
            Finding(
                category=FindingCategory.REFERENCES,
                severity=Severity.INFO,
                source=FindingSource.RULE_ENGINE,
                rule_id="references.count",
                message=t("rule.references.count", lang, n=count),
            )
        )

    normalized = [
        re.sub(r"\s+", " ", _ENTRY_NUMBER_PREFIX.sub("", e).lower()).strip() for e in entries
    ]
    duplicates = len(normalized) - len(set(normalized))
    if duplicates > rule.max_allowed_duplicate_sources:
        findings.append(
            Finding(
                category=FindingCategory.REFERENCES,
                severity=Severity.WARNING,
                source=FindingSource.RULE_ENGINE,
                rule_id="references.duplicates",
                message=t("rule.references.duplicates", lang, n=duplicates),
            )
        )

    empty_or_short = [e for e in entries if len(e) < 15]
    if empty_or_short:
        findings.append(
            Finding(
                category=FindingCategory.REFERENCES,
                severity=Severity.WARNING,
                source=FindingSource.RULE_ENGINE,
                rule_id="references.suspicious_entries",
                message=t("rule.references.suspicious", lang, n=len(empty_or_short)),
            )
        )

    return findings


def validate_in_text_citations(
    full_document_text: str, preset: RulePreset, lang: str = "ru"
) -> list[Finding]:
    if not preset.references.require_in_text_citations:
        return []
    citation_count = len(_IN_TEXT_CITATION.findall(full_document_text))
    if citation_count == 0:
        return [
            Finding(
                category=FindingCategory.REFERENCES,
                severity=Severity.WARNING,
                source=FindingSource.RULE_ENGINE,
                rule_id="references.in_text_citations",
                message=t("rule.references.in_text_missing", lang),
            )
        ]
    return [
        Finding(
            category=FindingCategory.REFERENCES,
            severity=Severity.INFO,
            source=FindingSource.RULE_ENGINE,
            rule_id="references.in_text_citations",
            message=t("rule.references.in_text_found", lang, n=citation_count),
        )
    ]
