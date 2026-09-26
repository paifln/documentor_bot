"""Rule Engine.

Runs every deterministic validator (no LLM involved) against a parsed
document and a RulePreset, and returns a flat list of Findings plus the
detected structure report (reused later by the AI pipeline for chunking).

`lang` selects the interface language (ru/kk/en) that all user-facing
Finding text is generated in — see app/i18n/translations.py.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from app.common.models import Finding
from app.document import structure as structure_module
from app.document.parser import ParsedDocument
from app.rules.models import RulePreset
from app.rules.validators import font as font_validator
from app.rules.validators import headings as headings_validator
from app.rules.validators import margins as margins_validator
from app.rules.validators import numbering as numbering_validator
from app.rules.validators import page as page_validator
from app.rules.validators import paragraphs as paragraphs_validator
from app.rules.validators import references as references_validator
from app.rules.validators import spacing as spacing_validator
from app.rules.validators import structure as structure_validator


@dataclass
class RuleEngineResult:
    findings: list[Finding]
    structure_report: structure_module.StructureReport
    sections_found: dict[str, bool]


class RuleEngine:
    """Stateless orchestrator — safe to reuse across requests."""

    def run(
        self, document: ParsedDocument, preset: RulePreset, lang: str = "ru"
    ) -> RuleEngineResult:
        findings: list[Finding] = []

        for index, page in enumerate(document.pages or [document.page], 1):
            section = replace(document, page=page)
            checks = page_validator.validate_page(section, preset, lang)
            checks += margins_validator.validate_margins(section, preset, lang)
            for finding in checks:
                finding.location = f"Section {index}: {finding.location}"
            findings += checks
        findings += page_validator.validate_headers_footers(document, preset, lang)

        findings += font_validator.validate_font(document, preset, lang)
        findings += font_validator.validate_paragraph_font_consistency(document, preset, lang)

        findings += spacing_validator.validate_spacing(document, preset, lang)
        findings += paragraphs_validator.validate_paragraphs(document, preset, lang)

        struct_report = structure_module.analyze_structure(document)
        findings += headings_validator.validate_headings(document, struct_report, preset, lang)
        findings += numbering_validator.validate_numbering(struct_report, lang)

        structure_findings, sections_found = structure_validator.validate_structure(
            struct_report, preset, lang
        )
        findings += structure_findings

        sections_text = structure_module.split_into_logical_sections(document, struct_report)
        from app.rules.validators.completeness import validate_completeness

        findings += validate_completeness(document, struct_report, sections_text, preset, lang)
        references_text = sections_text.get("references", "")
        findings += references_validator.validate_references(
            references_text, struct_report, preset, lang
        )
        findings += references_validator.validate_in_text_citations(
            "\n".join(
                v for k, v in sections_text.items() if k not in {"references", "content_table"}
            ),
            preset,
            lang,
        )

        return RuleEngineResult(
            findings=findings,
            structure_report=struct_report,
            sections_found=sections_found,
        )
