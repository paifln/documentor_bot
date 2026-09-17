from __future__ import annotations

from app.common.enums import Severity
from app.document.parser import parse_docx
from app.rules.validators.font import validate_font
from app.rules.validators.font import validate_paragraph_font_consistency


def test_correct_font_passes(correct_docx, sample_preset):
    document = parse_docx(correct_docx)
    findings = validate_font(document, sample_preset)
    main_finding = next(f for f in findings if f.rule_id == "font.main")
    assert main_finding.severity == Severity.PASS


def test_wrong_font_flagged(wrong_font_docx, sample_preset):
    document = parse_docx(wrong_font_docx)
    findings = validate_font(document, sample_preset)
    main_finding = next(f for f in findings if f.rule_id == "font.main")
    assert main_finding.severity == Severity.ERROR
    assert main_finding.expected == "Times New Roman, 14 pt"


def test_mixed_formatting_detects_paragraph_inconsistency(mixed_formatting_docx, sample_preset):
    document = parse_docx(mixed_formatting_docx)
    findings = validate_paragraph_font_consistency(document, sample_preset)
    assert len(findings) >= 1
