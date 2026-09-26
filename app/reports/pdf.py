"""PDF report generation (spec §19) using ReportLab.

Two things make this correct for Documentor's actual users (Kazakh/Russian
students) where a naive ReportLab setup would fail:

1. Unicode font registration (app/reports/fonts.py) — ReportLab's base-14
   fonts have zero Cyrillic glyphs, so without this every Cyrillic/Kazakh
   character renders as a black box ("tofu"). We register a real TTF that
   covers both.
2. Every string is looked up via app.i18n.t(key, lang) — the report is
   generated in whichever language the requesting user has selected, not
   hardcoded to one language.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.common.enums import Severity
from app.common.exceptions import ReportGenerationError
from app.common.models import CheckResult
from app.i18n import t
from app.reports.fonts import ensure_unicode_font_registered

_CATEGORY_KEYS = {
    "formatting": "category.formatting",
    "structure": "category.structure",
    "language": "category.language",
    "style": "category.style",
    "content": "category.content",
}

_DATE_LOCALE = {
    "ru": "ru_RU",
    "kk": "kk_KZ",
    "en": "en_US",
}  # informational only, not used for formatting


def _xml_escape(text: str) -> str:
    """Escape text for safe embedding in ReportLab's Paragraph markup
    (a restricted HTML/XML-like syntax). Anything that comes from the
    student's document — headings, AI-quoted text, filenames — can contain
    '&', '<', '>' (e.g. "R&D", "x < y", generic types like "List<T>"), which
    would otherwise break ReportLab's markup parser and abort the whole
    PDF build."""
    if not text:
        return text
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _build_styles(font_family: str):
    styles = getSampleStyleSheet()

    # Overwrite every base style's font with our Unicode-capable family so
    # nothing accidentally falls back to Helvetica mid-document.
    for style_name in ("Normal", "Title", "Heading2", "Heading3", "BodyText"):
        styles[style_name].fontName = font_family

    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName=f"{font_family}-Bold",
            fontSize=20,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            fontName=f"{font_family}-Bold",
            spaceBefore=14,
            spaceAfter=8,
            textColor=colors.HexColor("#1a1a2e"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="FindingBody",
            parent=styles["BodyText"],
            fontName=font_family,
            alignment=TA_LEFT,
            spaceAfter=6,
            leftIndent=6,
        )
    )
    return styles


def build_pdf_report(
    result: CheckResult,
    *,
    output_path: Path,
    document_display_name: str,
    institution: str,
    work_type_label: str,
    lang: str = "ru",
) -> Path:
    try:
        font_family = ensure_unicode_font_registered()
        styles = _build_styles(font_family)
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
        )
        story = []

        story.append(Paragraph("DOCUMENTOR", styles["ReportTitle"]))
        story.append(Paragraph(t("pdf.title", lang), styles["Heading3"]))
        story.append(Spacer(1, 8))
        story.append(
            Paragraph(
                f"<b>{t('pdf.file', lang)}:</b> {_xml_escape(document_display_name)}",
                styles["Normal"],
            )
        )
        story.append(
            Paragraph(
                f"<b>{t('pdf.institution', lang)}:</b> {_xml_escape(institution)}", styles["Normal"]
            )
        )
        story.append(
            Paragraph(
                f"<b>{t('pdf.work_type', lang)}:</b> {_xml_escape(work_type_label)}",
                styles["Normal"],
            )
        )
        story.append(
            Paragraph(
                f"<b>{t('pdf.date', lang)}:</b> {dt.datetime.now().strftime('%d.%m.%Y %H:%M')}",
                styles["Normal"],
            )
        )
        story.append(
            Paragraph(
                f"<b>{t('pdf.total', lang)}:</b> {result.score:.0f} / {result.max_score:.0f}",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 14))

        # 1. Category scores table
        story.append(Paragraph(t("pdf.section1", lang), styles["SectionHeading"]))
        table_data = [[t("pdf.table.category", lang), t("pdf.table.points", lang)]]
        for cs in result.category_scores:
            label = t(_CATEGORY_KEYS.get(cs.category.value, cs.category.value), lang)
            table_data.append(
                [
                    label,
                    f"{cs.earned_points:.0f}/{cs.max_points:.0f}"
                    if cs.evaluated
                    else t("not_evaluated", lang),
                ]
            )
        table = Table(table_data, colWidths=[100 * mm, 40 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), font_family),
                    ("FONTNAME", (0, 0), (-1, 0), f"{font_family}-Bold"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8f5")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f7f7fb")],
                    ),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 10))

        summary = result.summary
        story.append(
            Paragraph(
                f"{t('summary.critical', lang, n=summary.critical)} &nbsp;&nbsp; "
                f"{t('summary.errors', lang, n=summary.errors)} &nbsp;&nbsp; "
                f"{t('summary.warnings', lang, n=summary.warnings)} &nbsp;&nbsp; "
                f"{t('summary.passed', lang, n=summary.passed)}",
                styles["Normal"],
            )
        )

        # 2. Formatting issues
        formatting_findings = [
            f
            for f in result.findings
            if f.category.value == "formatting" and f.severity != Severity.PASS
        ]
        story.append(Paragraph(t("pdf.section2", lang), styles["SectionHeading"]))
        if not formatting_findings:
            story.append(Paragraph(t("pdf.section2.none", lang), styles["FindingBody"]))
        for f in formatting_findings:
            story.append(_finding_paragraph(f, styles, lang))

        # 3. Structure
        structure_findings = [
            f
            for f in result.findings
            if f.category.value in ("structure", "references") and f.severity != Severity.PASS
        ]
        story.append(Paragraph(t("pdf.section3", lang), styles["SectionHeading"]))
        if not structure_findings:
            story.append(Paragraph(t("pdf.section3.none", lang), styles["FindingBody"]))
        for f in structure_findings:
            story.append(_finding_paragraph(f, styles, lang))

        # 4. Text analysis (AI)
        text_findings = [
            f for f in result.findings if f.category.value in ("language", "style", "content")
        ]
        story.append(Paragraph(t("pdf.section4", lang), styles["SectionHeading"]))
        if not result.ai_analysis_available:
            story.append(Paragraph(t("pdf.section4.partial", lang), styles["FindingBody"]))
        if not text_findings:
            story.append(Paragraph(t("pdf.section4.none", lang), styles["FindingBody"]))
        for f in text_findings:
            story.append(_finding_paragraph(f, styles, lang, show_quote=True))

        story.append(Spacer(1, 16))
        story.append(Paragraph(f"<i>{t('pdf.footer', lang)}</i>", styles["Normal"]))

        doc.build(story)
        return output_path
    except Exception as exc:  # noqa: BLE001
        raise ReportGenerationError(str(exc)) from exc


def _finding_paragraph(finding, styles, lang: str, show_quote: bool = False):
    location = _xml_escape(finding.location) or finding.category.value
    message = _xml_escape(finding.message)
    text = f"{finding.severity.emoji} <b>{location}</b><br/>{message}"
    if finding.expected and finding.actual:
        text += "<br/>" + t(
            "pdf.expected_actual",
            lang,
            expected=_xml_escape(finding.expected),
            actual=_xml_escape(finding.actual),
        )
    if show_quote and finding.original_text:
        safe_quote = _xml_escape(finding.original_text)
        text += f'<br/>{t("pdf.quote_label", lang)}: "{safe_quote}"'
    if finding.suggestion:
        text += f"<br/>💡 {_xml_escape(finding.suggestion)}"
    if finding.source.value == "ai" and finding.confidence is not None:
        pct = round(finding.confidence * 100)
        text += f"<br/><font size=8 color='grey'>{t('source.ai', lang)} · {t('confidence_label', lang, pct=pct)}</font>"
    elif finding.source.value == "rule_engine":
        text += f"<br/><font size=8 color='grey'>{t('source.rule_engine', lang)}</font>"
    return Paragraph(text, styles["FindingBody"])
