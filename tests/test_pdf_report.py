from __future__ import annotations

from app.common.enums import FindingCategory, FindingSource, Severity
from app.common.models import CategoryScore, CheckResult, CheckSummary, Finding
from app.reports.pdf import build_pdf_report


def test_failed_report_refresh_keeps_previous_pdf_and_cleans_temporary(monkeypatch, sample_preset):
    import pytest
    from app.config.settings import get_settings
    from app.reports import generator

    previous = get_settings().reports_dir / "report_9.pdf"
    previous.write_bytes(b"previous report")

    def fail(result, *, output_path, **kwargs):
        output_path.write_bytes(b"incomplete report")
        raise RuntimeError("render failed")

    monkeypatch.setattr(generator, "build_pdf_report", fail)
    with pytest.raises(RuntimeError):
        generator.generate_pdf(
            CheckResult(score=0, summary=CheckSummary()), sample_preset, "work.docx", 9
        )
    assert previous.read_bytes() == b"previous report"
    assert not list(previous.parent.glob("*.tmp.pdf"))


def test_pdf_text_preserves_kazakh_and_marks_unsupported_characters():
    from app.reports.text import pdf_text

    assert pdf_text("Әә Ғғ Ққ Ңң Өө Ұұ Үү Һһ Іі") == "Әә Ғғ Ққ Ңң Өө Ұұ Үү Һһ Іі"
    assert pdf_text("A\x00B\u200bC") == "ABC"
    assert "[U+10FFFF]" in pdf_text("\U0010ffff")
    assert pdf_text("x < y & z") == "x &lt; y &amp; z"


def test_pdf_report_generates_file(tmp_path):
    result = CheckResult(
        score=84,
        summary=CheckSummary(critical=1, errors=2, warnings=3, passed=10),
        category_scores=[
            CategoryScore(category=FindingCategory.FORMATTING, max_points=30, earned_points=27),
        ],
        findings=[
            Finding(
                category=FindingCategory.FORMATTING,
                severity=Severity.ERROR,
                source=FindingSource.RULE_ENGINE,
                location="Левое поле",
                message="Левое поле не соответствует требованиям.",
                expected="30 мм",
                actual="20 мм",
            ),
            Finding(
                category=FindingCategory.STYLE,
                severity=Severity.WARNING,
                source=FindingSource.AI,
                location="Введение",
                message="Разговорная формулировка.",
                original_text="Я хочу рассказать...",
                suggestion="В работе рассматривается...",
                confidence=0.9,
            ),
        ],
    )
    output_path = tmp_path / "report.pdf"
    path = build_pdf_report(
        result,
        output_path=output_path,
        document_display_name="test.docx",
        institution="Makhambet University",
        work_type_label="Курсовая работа",
    )
    assert path.exists()
    assert path.stat().st_size > 0


def test_pdf_report_handles_special_characters_without_crashing(tmp_path):
    """Regression test: document-derived text (headings, AI messages) can
    contain raw '&', '<', '>' — e.g. "AT&T", "List<T>", "x < y" — which are
    meaningful characters in ReportLab's Paragraph markup. Unescaped, these
    either corrupt the rendered text or crash PDF generation outright."""
    result = CheckResult(
        score=70,
        summary=CheckSummary(critical=0, errors=1, warnings=1, passed=5),
        category_scores=[
            CategoryScore(category=FindingCategory.FORMATTING, max_points=30, earned_points=25),
        ],
        findings=[
            Finding(
                category=FindingCategory.FORMATTING,
                severity=Severity.ERROR,
                source=FindingSource.RULE_ENGINE,
                location="Глава 1 <Введение> & обзор",
                message="Использование List<T> & Dict<K,V> без пояснений.",
                expected="a < b",
                actual="a > b & c",
                suggestion="Замените AT&T на полное название.",
            ),
            Finding(
                category=FindingCategory.STYLE,
                severity=Severity.WARNING,
                source=FindingSource.AI,
                location="Введение",
                message="Незакрытая конструкция вида <b без пары.",
                original_text="x < y & z > 10, а также <неправильный тег",
                confidence=0.8,
            ),
        ],
    )
    output_path = tmp_path / "report_special_chars.pdf"
    path = build_pdf_report(
        result,
        output_path=output_path,
        document_display_name="R&D <report>.docx",
        institution="Makhambet University",
        work_type_label="Курсовая работа",
    )
    assert path.exists()
    assert path.stat().st_size > 0
