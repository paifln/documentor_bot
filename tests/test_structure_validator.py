from __future__ import annotations

from app.document.parser import parse_docx
from app.document.structure import analyze_structure
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
