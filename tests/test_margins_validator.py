from __future__ import annotations

from app.common.enums import Severity
from app.document.parser import parse_docx
from app.rules.validators.margins import validate_margins


def test_correct_margins_pass(correct_docx, sample_preset):
    document = parse_docx(correct_docx)
    findings = validate_margins(document, sample_preset)
    assert all(f.severity == Severity.PASS for f in findings)


def test_wrong_margins_flagged(wrong_margins_docx, sample_preset):
    document = parse_docx(wrong_margins_docx)
    findings = validate_margins(document, sample_preset)
    errors = [f for f in findings if f.severity == Severity.ERROR]
    assert len(errors) > 0
    assert any(f.rule_id == "margins.left_margin" for f in errors)
