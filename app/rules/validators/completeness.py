"""Rules that require both effective paragraph formatting and section boundaries."""

from app.common.enums import FindingCategory, FindingSource, Severity
from app.common.models import Finding
from app.i18n import t


def validate_completeness(document, structure, sections, preset, lang):
    findings = []
    for key, minimum in (
        ("introduction", preset.structure.min_words_introduction),
        ("conclusion", preset.structure.min_words_conclusion),
    ):
        if key not in sections:
            continue
        count = len("\n".join(sections[key].splitlines()[1:]).split())
        if count < minimum:
            findings.append(
                Finding(
                    category=FindingCategory.STRUCTURE,
                    severity=Severity.WARNING,
                    source=FindingSource.RULE_ENGINE,
                    rule_id=f"structure.min_words.{key}",
                    location=t(f"section.{key}", lang),
                    message=t("rule.min_words", lang),
                    expected=str(minimum),
                    actual=str(count),
                )
            )
    for heading in structure.headings:
        p = document.paragraphs[heading.paragraph_index]
        if (
            preset.headings.require_page_break_before_top_level
            and heading.level == 1
            and p.index > 0
            and not p.page_break_before
        ):
            findings.append(
                Finding(
                    category=FindingCategory.FORMATTING,
                    severity=Severity.WARNING,
                    source=FindingSource.RULE_ENGINE,
                    rule_id="headings.page_break",
                    location=heading.raw_text[:250],
                    message=t("rule.page_break", lang),
                )
            )
        if not preset.font.allow_headings_bold and any(r.bold for r in p.runs):
            findings.append(
                Finding(
                    category=FindingCategory.FORMATTING,
                    severity=Severity.WARNING,
                    source=FindingSource.RULE_ENGINE,
                    rule_id="headings.bold",
                    location=heading.raw_text[:250],
                    message=t("rule.heading_bold", lang),
                )
            )
    return findings
