from __future__ import annotations

from app.common.enums import FindingCategory, FindingSource, Severity
from app.common.models import Finding
from app.document.structure import StructureReport
from app.i18n import t


def validate_numbering(structure: StructureReport, lang: str = "ru") -> list[Finding]:
    """Surface the numbering/level-sequence issues detected in
    app.document.structure as user-facing Findings."""
    findings: list[Finding] = []

    for prev, curr in structure.numbering_error_pairs:
        findings.append(
            Finding(
                category=FindingCategory.FORMATTING,
                severity=Severity.WARNING,
                source=FindingSource.RULE_ENGINE,
                rule_id="numbering.sequence",
                message=t("rule.numbering.sequence_error", lang, prev=prev, curr=curr),
            )
        )

    for heading_text, prev_level, curr_level in structure.level_error_details:
        findings.append(
            Finding(
                category=FindingCategory.FORMATTING,
                severity=Severity.WARNING,
                source=FindingSource.RULE_ENGINE,
                rule_id="numbering.level_jump",
                message=t(
                    "rule.numbering.level_jump",
                    lang,
                    heading=heading_text,
                    prev=prev_level,
                    curr=curr_level,
                ),
            )
        )

    if not structure.numbering_errors and not structure.level_errors and structure.headings:
        findings.append(
            Finding(
                category=FindingCategory.FORMATTING,
                severity=Severity.PASS,
                source=FindingSource.RULE_ENGINE,
                rule_id="numbering.ok",
                message=t("rule.numbering.ok", lang),
            )
        )

    return findings
