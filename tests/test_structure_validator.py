from __future__ import annotations

from docx import Document
from docx.shared import Cm

from app.document.parser import parse_docx
from app.document.structure import analyze_structure
from app.rules.engine import RuleEngine
from app.rules.presets.loader import PresetRegistry
from app.rules.validators.structure import validate_structure


def test_all_sections_detected_in_correct_docx(correct_docx):
    document = parse_docx(correct_docx)
    structure = analyze_structure(document)
    assert "introduction" in structure.detected_sections
    assert "conclusion" in structure.detected_sections
    assert "references" in structure.detected_sections


def test_missing_sections_flagged(missing_sections_docx, sample_preset):
    document = parse_docx(missing_sections_docx)
    structure = analyze_structure(document)
    findings, sections_found = validate_structure(structure, sample_preset)

    assert sections_found["practical_part"] is False
    assert sections_found["references"] is False

    critical = [f for f in findings if f.severity.value == "critical"]
    assert len(critical) >= 2


def test_diploma_accepts_topic_named_chapter_and_checks_reference_minimum(tmp_path):
    doc = Document()
    doc.sections[0].bottom_margin = Cm(2.5)
    doc.styles["Normal"].paragraph_format.line_spacing = 1.0
    for title in ("СОДЕРЖАНИЕ", "ВВЕДЕНИЕ", "1 МЕТОДЫ ИССЛЕДОВАНИЯ", "ЗАКЛЮЧЕНИЕ"):
        heading = doc.add_heading(title, level=1)
        heading.paragraph_format.first_line_indent = Cm(1.25)
        heading.runs[0].bold = True
        doc.add_paragraph("Текст раздела.")
    doc.add_heading("Список использованной литературы.", level=1)
    doc.add_paragraph("1 Источник исследования")
    path = tmp_path / "diploma.docx"
    doc.save(path)

    preset = PresetRegistry().get("makhambet_diploma")
    result = RuleEngine().run(parse_docx(path), preset)

    assert result.sections_found["content_table"]
    assert result.sections_found["main_body"]
    assert preset.margins.bottom_mm == 25
    assert preset.paragraph.line_spacing == 1.0
    assert [
        f.location for f in result.findings if f.rule_id == "headings.top_level_format"
    ] == ["Список использованной литературы."]
    minimum = next(f for f in result.findings if f.rule_id == "references.min_count")
    assert minimum.expected == ">= 30"
    assert minimum.severity.value in {"warning", "error"}
