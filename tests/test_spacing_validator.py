from __future__ import annotations

from app.common.enums import Severity
from app.document.parser import parse_docx
from app.rules.validators.spacing import validate_spacing


def test_correct_spacing_passes(correct_docx, sample_preset):
    document = parse_docx(correct_docx)
    findings = validate_spacing(document, sample_preset)
    assert any(f.severity == Severity.PASS for f in findings)


def test_wrong_spacing_flagged(wrong_spacing_docx, sample_preset):
    document = parse_docx(wrong_spacing_docx)
    findings = validate_spacing(document, sample_preset)
    assert any(f.severity == Severity.ERROR for f in findings)
