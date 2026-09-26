"""Validation of uploaded files before any parsing is attempted.

This is deliberately conservative: we validate the ZIP/OOXML container
structure ourselves rather than trusting the Telegram-reported MIME type
(which is client-supplied and therefore untrustworthy) or the file
extension alone.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from app.common.exceptions import CorruptedDocumentError, UnsupportedFormatError
from app.config.settings import get_settings

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
            settings = get_settings()
            parts = zf.infolist()
            if len(parts) > settings.max_archive_parts:
                return ValidationResult(False, "too many archive parts")
            if sum(p.file_size for p in parts) > settings.max_uncompressed_mb * 1024**2:
                return ValidationResult(False, "uncompressed archive exceeds limit")
            for part in parts:
                name = part.filename.replace("\\", "/")
                if (
                    name.startswith("/")
                    or ":" in name
                    or ".." in PurePosixPath(name).parts
                    or part.flag_bits & 1
                ):
                    return ValidationResult(False, "unsafe or encrypted archive part")
                if part.file_size > settings.max_archive_part_mb * 1024**2:
                    return ValidationResult(False, "archive part exceeds limit")
                if part.file_size > max(1, part.compress_size) * settings.max_compression_ratio:
                    return ValidationResult(False, "excessive compression ratio")
            names = set(zf.namelist())
            if len(names) != len(parts):
                return ValidationResult(False, "duplicate archive part")
            missing = [p for p in _REQUIRED_PARTS if p not in names]
            if missing:
                return ValidationResult(False, f"missing required parts: {missing}")
            # Read in bounded blocks and verify CRC only after metadata limits.
            total = 0
            for part in parts:
                with zf.open(part) as stream:
                    tail = b""
                    while block := stream.read(64 * 1024):
                        total += len(block)
                        if total > settings.max_uncompressed_mb * 1024**2:
                            return ValidationResult(False, "expanded data exceeds limit")
                        scan = (tail + block).replace(b"\x00", b"")
                        if part.filename.endswith(".xml") and b"<!DOCTYPE" in scan:
                            return ValidationResult(False, "DTD is not permitted")
                        tail = block[-32:]
            # Reject archives with suspiciously deep/absolute paths (zip-slip).
            for name in names:
                if name.startswith("/") or ".." in Path(name).parts:
                    return ValidationResult(False, f"unsafe archive entry: {name}")
    except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError) as exc:
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
