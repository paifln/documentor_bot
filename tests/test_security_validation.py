from __future__ import annotations

import zipfile

import pytest

from app.common.exceptions import CorruptedDocumentError, UnsupportedFormatError
from app.security.validation import run_all_validations


def test_valid_docx_passes(correct_docx):
    run_all_validations(correct_docx, "correct.docx", None)  # should not raise


def test_wrong_extension_rejected(correct_docx):
    with pytest.raises(UnsupportedFormatError):
        run_all_validations(correct_docx, "correct.txt", None)


def test_corrupted_zip_rejected(tmp_path):
    bad_file = tmp_path / "broken.docx"
    bad_file.write_bytes(b"PK\x03\x04not a real zip content")
    with pytest.raises(CorruptedDocumentError):
        run_all_validations(bad_file, "broken.docx", None)


def test_zip_missing_document_xml_rejected(tmp_path):
    fake_docx = tmp_path / "fake.docx"
    with zipfile.ZipFile(fake_docx, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("word/not_the_document.xml", "<xml/>")
    with pytest.raises(CorruptedDocumentError):
        run_all_validations(fake_docx, "fake.docx", None)
