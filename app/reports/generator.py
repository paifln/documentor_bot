"""Builds the different presentations of a CheckResult:
  * short Telegram summary (spec §2)
  * "Errors" view
  * "Recommendations" view
  * PDF (delegates to app.reports.pdf)

Every string here goes through app.i18n.t(key, lang) so the same
CheckResult can be rendered in whichever language the user selected —
UX copy changes never touch the analysis pipeline (spec §35: plain
language, no technical jargon).
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.common.enums import Severity
from app.common.models import CheckResult
from app.config.settings import get_settings
from app.i18n import t
from app.reports.pdf import build_pdf_report
from app.reports.presentation import category_value, score_note, score_over_100
from app.document.labels import display_location
from app.rules.models import RulePreset

_WORK_TYPE_KEYS = {
    "coursework": "work_type.coursework",
    "diploma": "work_type.diploma",
    "report": "work_type.report",
    "essay": "work_type.essay",
}
_CATEGORY_KEYS = {
    "formatting": "category.formatting",
    "structure": "category.structure",
    "language": "category.language",
    "style": "category.style",
    "content": "category.content",
}


def build_summary_message(result: CheckResult, lang: str = "ru") -> str:
    s = result.summary
    lines = [
        t("summary.title", lang),
        "",
        t("summary.score", lang, score=score_over_100(result), max_score=100),
        "",
        t("summary.critical", lang, n=s.critical),
        t("summary.errors", lang, n=s.errors),
        t("summary.warnings", lang, n=s.warnings),
        t("summary.passed", lang, n=s.passed),
        "",
    ]
    lines.append(score_note(result, lang))
    lines.append(t("pdf.diagnostic", lang))
    if result.preset_status != "department_verified":
        lines.append(t("pdf.unverified", lang))
    lines.append(t("summary.footer", lang))
    return "\n".join(lines)


def build_errors_message(result: CheckResult, lang: str = "ru") -> str:
    problems = [f for f in result.findings if f.severity in (Severity.CRITICAL, Severity.ERROR)]
    if not problems:
        return t("errors.none", lang)

    lines = [t("errors.title", lang)]
    for f in problems[:30]:
        lines.append(_finding_line(f, lang))
        lines.append("")
    if len(problems) > 30:
        lines.append(t("errors.more", lang, n=len(problems) - 30))
    return "\n".join(lines)


def build_recommendations_message(result: CheckResult, lang: str = "ru") -> str:
    recs = [f for f in result.findings if f.suggestion]
    if not recs:
        return t("recommendations.none", lang)

    lines = [t("recommendations.title", lang)]
    for f in recs[:20]:
        lines.append(f"• {f.suggestion}")
        if f.location:
            lines.append(f"  ({display_location(f.location, lang)})")
    if len(recs) > 20:
        lines.append(t("recommendations.more", lang, n=len(recs) - 20))
    return "\n".join(lines)


def build_results_message(result: CheckResult, lang: str = "ru") -> str:
    lines = [t("results.category_scores_title", lang), ""]
    for cs in result.category_scores:
        label = t(_CATEGORY_KEYS.get(cs.category.value, cs.category.value), lang)
        lines.append(f"{label}: {category_value(cs, lang)}")
    lines.append("")
    lines.append(t("results.total", lang, score=score_over_100(result), max_score=100))
    lines.append(score_note(result, lang))
    return "\n".join(lines)


def _finding_line(finding, lang: str) -> str:
    line = f"{finding.severity.emoji} {finding.message}"
    if finding.location:
        line += f"\n   {display_location(finding.location, lang)}"
    if finding.expected and finding.actual:
        line += "\n   " + t(
            "pdf.expected_actual", lang, expected=finding.expected, actual=finding.actual
        )
    if finding.suggestion:
        line += f"\n   💡 {finding.suggestion}"
    if finding.confidence is not None:
        line += f"\n   {t('confidence_label', lang, pct=round(finding.confidence * 100))}"
    return line


def generate_pdf(
    result: CheckResult,
    preset: RulePreset,
    document_display_name: str,
    check_id: int,
    lang: str = "ru",
) -> Path:
    settings = get_settings()
    output_path = settings.reports_dir / f"report_{check_id}.pdf"
    temporary = output_path.with_name(f"report_{check_id}.{uuid4().hex}.tmp.pdf")
    try:
        build_pdf_report(
            result,
            output_path=temporary,
            document_display_name=document_display_name,
            institution=preset.institution,
            work_type_label=t(
                _WORK_TYPE_KEYS.get(preset.work_type.value, preset.work_type.value), lang
            ),
            lang=lang,
        )
        temporary.replace(output_path)
    finally:
        temporary.unlink(missing_ok=True)
    return output_path
