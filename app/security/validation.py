"""Validation of uploaded files before any parsing is attempted.

This is deliberately conservative: we validate the ZIP/OOXML container
structure ourselves rather than trusting the Telegram-reported MIME type
(which is client-supplied and therefore untrustworthy) or the file
extension alone.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

from app.common.exceptions import CorruptedDocumentError, UnsupportedFormatError

_DOCX_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

_REQUIRED_PARTS = ("[Content_Types].xml", "word/document.xml")


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    reason: str = ""


def validate_mime_type(reported_mime: str | None) -> ValidationResult:
    if reported_mime and reported_mime not in _DOCX_MIME_TYPES:
        return ValidationResult(False, f"unexpected mime type: {reported_mime}")
    return ValidationResult(True)


def validate_extension(filename: str) -> ValidationResult:
    if not filename.lower().endswith(".docx"):
        return ValidationResult(False, "extension is not .docx")
    return ValidationResult(True)


def validate_docx_container(path: Path) -> ValidationResult:
    """Open as a ZIP and confirm required OOXML parts are present.

    This catches: renamed non-docx files, corrupted archives, and files
    that are technically ZIPs but not Word documents (e.g. .xlsx renamed).
    """
    try:
        with zipfile.ZipFile(path) as zf:
            bad_entry = zf.testzip()
            if bad_entry is not None:
                return ValidationResult(False, f"corrupted zip entry: {bad_entry}")
            names = set(zf.namelist())
            missing = [p for p in _REQUIRED_PARTS if p not in names]
            if missing:
                return ValidationResult(False, f"missing required parts: {missing}")
            # Reject archives with suspiciously deep/absolute paths (zip-slip).
            for name in names:
                if name.startswith("/") or ".." in Path(name).parts:
                    return ValidationResult(False, f"unsafe archive entry: {name}")
    except zipfile.BadZipFile as exc:
        return ValidationResult(False, f"not a valid zip archive: {exc}")
    return ValidationResult(True)


def run_all_validations(path: Path, filename: str, reported_mime: str | None) -> None:
    """Raise the appropriate CourseworkCheckerError if anything fails."""
    ext_result = validate_extension(filename)
    if not ext_result.ok:
        raise UnsupportedFormatError(ext_result.reason)

    mime_result = validate_mime_type(reported_mime)
    if not mime_result.ok:
        raise UnsupportedFormatError(mime_result.reason)

    container_result = validate_docx_container(path)
    if not container_result.ok:
        raise CorruptedDocumentError(container_result.reason)
