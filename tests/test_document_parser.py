from __future__ import annotations

from app.document.parser import parse_docx


def test_parse_correct_docx_extracts_paragraphs(correct_docx):
    document = parse_docx(correct_docx)
    assert len(document.paragraphs) > 0
    assert document.full_text.strip() != ""


def test_parse_extracts_page_margins(correct_docx):
    document = parse_docx(correct_docx)
    assert abs(document.page.margin_left_mm - 30) < 1
    assert abs(document.page.margin_top_mm - 20) < 1


def test_parse_detects_dominant_font(correct_docx):
    document = parse_docx(correct_docx)
    name, size = document.dominant_font
    assert name == "Times New Roman"
    assert size == 14


def test_parse_wrong_font_detects_arial(wrong_font_docx):
    document = parse_docx(wrong_font_docx)
    name, size = document.dominant_font
    assert name == "Arial"
    assert size == 12
