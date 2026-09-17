from __future__ import annotations

from app.common.enums import FindingCategory, FindingSource, Severity
from app.common.models import Finding
from app.document.structure import StructureReport
from app.i18n import t
from app.rules.models import RulePreset

# Canonical section keys the RulePreset YAML uses (language-independent —
# see rules/presets/*.yaml). Display labels are looked up via i18n so the
# same preset works no matter which language the user picks.
_SECTION_LABEL_KEYS: dict[str, str] = {
    "introduction": "section.introduction",
    "theoretical_part": "section.theoretical_part",
    "practical_part": "section.practical_part",
    "main_body": "section.main_body",
    "conclusion": "section.conclusion",
    "references": "section.references",
    "appendix": "section.appendix",
}


def validate_structure(
    structure: StructureReport, preset: RulePreset, lang: str = "ru"
) -> tuple[list[Finding], dict[str, bool]]:
    findings: list[Finding] = []
    sections_found: dict[str, bool] = {}

    for key in preset.structure.required_sections:
        label = t(_SECTION_LABEL_KEYS.get(key, key), lang)
        found = key in structure.detected_sections
        sections_found[key] = found
        if found:
            findings.append(
                Finding(
                    category=FindingCategory.STRUCTURE,
                    severity=Severity.PASS,
                    source=FindingSource.RULE_ENGINE,
                    rule_id=f"structure.section.{key}",
                    message=t("rule.structure.section_present", lang, label=label),
                )
            )
        else:
            findings.append(
                Finding(
                    category=FindingCategory.STRUCTURE,
                    severity=Severity.CRITICAL,
                    source=FindingSource.RULE_ENGINE,
                    rule_id=f"structure.section.{key}",
                    message=t("rule.structure.section_missing", lang, label=label),
                    suggestion=t("rule.structure.section_missing.suggestion", lang, label=label),
                )
            )

    for key in preset.structure.optional_sections:
        label = t(_SECTION_LABEL_KEYS.get(key, key), lang)
        found = key in structure.detected_sections
        sections_found[key] = found
        if not found:
            findings.append(
                Finding(
                    category=FindingCategory.STRUCTURE,
                    severity=Severity.INFO,
                    source=FindingSource.RULE_ENGINE,
                    rule_id=f"structure.optional.{key}",
                    message=t("rule.structure.optional_missing", lang, label=label),
                )
            )

    return findings, sections_found
