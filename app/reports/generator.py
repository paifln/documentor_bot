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

from app.common.enums import Severity
from app.common.models import CheckResult
from app.config.settings import get_settings
from app.i18n import t
from app.reports.pdf import build_pdf_report
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
        t("summary.score", lang, score=result.score, max_score=result.max_score),
        "",
        t("summary.critical", lang, n=s.critical),
        t("summary.errors", lang, n=s.errors),
        t("summary.warnings", lang, n=s.warnings),
        t("summary.passed", lang, n=s.passed),
        "",
    ]
    if not result.ai_analysis_available:
        lines.append(t("summary.ai_partial", lang))
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
            lines.append(f"  ({f.location})")
    if len(recs) > 20:
        lines.append(t("recommendations.more", lang, n=len(recs) - 20))
    return "\n".join(lines)


def build_results_message(result: CheckResult, lang: str = "ru") -> str:
    lines = [t("results.category_scores_title", lang), ""]
    for cs in result.category_scores:
        label = t(_CATEGORY_KEYS.get(cs.category.value, cs.category.value), lang)
        lines.append(
            f"{label}: {cs.earned_points:.0f}/{cs.max_points:.0f}"
            if cs.evaluated
            else f"{label}: {t('not_evaluated', lang)}"
        )
    lines.append("")
    lines.append(t("results.total", lang, score=result.score, max_score=result.max_score))
    return "\n".join(lines)


def _finding_line(finding, lang: str) -> str:
    line = f"{finding.severity.emoji} {finding.message}"
    if finding.location:
        line += f"\n   {finding.location}"
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
    temporary = output_path.with_suffix(".tmp.pdf")
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
    return output_path
