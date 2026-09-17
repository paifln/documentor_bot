from __future__ import annotations

from app.common.enums import FindingCategory, FindingSource, Severity
from app.common.models import Finding
from app.document.formatting import body_paragraphs, font_usage_breakdown
from app.document.parser import ParsedDocument
from app.i18n import t
from app.rules.models import RulePreset


def validate_font(document: ParsedDocument, preset: RulePreset, lang: str = "ru") -> list[Finding]:
    """Check the dominant document font/size against the preset, and flag
    any meaningfully-sized "foreign" font/size mixture (spec §5)."""
    findings: list[Finding] = []
    rule = preset.font
    stats = font_usage_breakdown(document)

    if not stats:
        findings.append(
            Finding(
                category=FindingCategory.FORMATTING,
                severity=Severity.WARNING,
                source=FindingSource.RULE_ENGINE,
                rule_id="font.name",
                message=t("rule.font.undetected", lang),
            )
        )
        return findings

    dominant = stats[0]
    name_ok = (dominant.name or "").strip().lower() == rule.name.strip().lower()
    size_ok = dominant.size_pt is not None and abs(dominant.size_pt - rule.size_pt) <= rule.tolerance_pt

    if name_ok and size_ok:
        findings.append(
            Finding(
                category=FindingCategory.FORMATTING,
                severity=Severity.PASS,
                source=FindingSource.RULE_ENGINE,
                rule_id="font.main",
                message=t("rule.font.main.pass", lang, name=rule.name, size=rule.size_pt),
            )
        )
    else:
        actual_desc = f"{dominant.name or '—'}, {dominant.size_pt or '—'} pt"
        findings.append(
            Finding(
                category=FindingCategory.FORMATTING,
                severity=Severity.ERROR,
                source=FindingSource.RULE_ENGINE,
                rule_id="font.main",
                location=t("label.main_text", lang),
                message=t("rule.font.main.error", lang),
                expected=f"{rule.name}, {rule.size_pt} pt",
                actual=actual_desc,
            )
        )

    # Foreign font / size share
    matching_share = sum(
        s.percentage
        for s in stats
        if (s.name or "").strip().lower() == rule.name.strip().lower()
        and s.size_pt is not None
        and abs(s.size_pt - rule.size_pt) <= rule.tolerance_pt
    )
    foreign_share = round(100 - matching_share, 1)
    if foreign_share > rule.max_foreign_font_share_pct:
        foreign_desc = ", ".join(
            f"{s.name or '—'} {s.size_pt or '—'} pt — {s.percentage}%"
            for s in stats[:5]
            if not (
                (s.name or "").strip().lower() == rule.name.strip().lower()
                and s.size_pt is not None
                and abs(s.size_pt - rule.size_pt) <= rule.tolerance_pt
            )
        )
        findings.append(
            Finding(
                category=FindingCategory.FORMATTING,
                severity=Severity.WARNING,
                source=FindingSource.RULE_ENGINE,
                rule_id="font.mixed",
                location=t("label.whole_document", lang),
                message=t("rule.font.mixed", lang),
                expected=f"{rule.name}, {rule.size_pt} pt — 100%",
                actual=foreign_desc or f"{foreign_share}%",
            )
        )

    return findings


def validate_paragraph_font_consistency(
    document: ParsedDocument, preset: RulePreset, lang: str = "ru"
) -> list[Finding]:
    """Flag individual body paragraphs whose dominant run font/size clearly
    diverges from the required font — with a location, so the student can
    find and fix it (spec §5 example)."""
    findings: list[Finding] = []
    rule = preset.font
    mismatches: list[int] = []

    for p in body_paragraphs(document):
        name, size = p.dominant_font
        if name is None and size is None:
            continue
        name_ok = (name or "").strip().lower() == rule.name.strip().lower()
        size_ok = size is not None and abs(size - rule.size_pt) <= rule.tolerance_pt
        if not (name_ok and size_ok):
            mismatches.append(p.index)

    if mismatches:
        sample = ", ".join(str(i + 1) for i in mismatches[:10])
        more = f" (+{len(mismatches) - 10})" if len(mismatches) > 10 else ""
        findings.append(
            Finding(
                category=FindingCategory.FORMATTING,
                severity=Severity.WARNING,
                source=FindingSource.RULE_ENGINE,
                rule_id="font.paragraph_consistency",
                location=t("label.paragraphs", lang, list=f"{sample}{more}"),
                message=t("rule.font.paragraph_consistency", lang),
                expected=f"{rule.name}, {rule.size_pt} pt",
            )
        )
    return findings
