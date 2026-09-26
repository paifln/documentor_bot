from __future__ import annotations

import re
import secrets
import unicodedata
from pathlib import Path
from typing import Any

# For *display* filenames we only need to strip characters that are
# actually dangerous or break rendering: control characters, path
# separators (path-traversal defense in depth — the real on-disk name is
# always a random token from safe_filename(), never this), and the
# classic Windows-reserved filename characters. Everything else — letters
# from any script (Cyrillic, Kazakh, Latin), digits, spaces, punctuation —
# is left untouched, since most of our users name files in Russian/Kazakh
# and a filename reduced to "_______.docx" is not acceptable UX.
_UNSAFE_FILENAME_CHARS = re.compile(r'[\x00-\x1f\x7f/\\:*?"<>|]+')


def safe_filename(original_name: str, *, prefix: str = "") -> str:
    """Generate a random, filesystem-safe filename.

    We never trust the original filename from a user (path traversal,
    unicode tricks, control characters). Only the extension is preserved.
    """
    suffix = Path(original_name).suffix.lower()
    if suffix not in {".docx"}:
        suffix = ".bin"
    token = secrets.token_hex(16)
    return f"{prefix}{token}{suffix}"


def sanitize_display_name(name: str) -> str:
    """Sanitize a filename for *display* purposes only (never for filesystem use)."""
    normalized = unicodedata.normalize("NFKC", name)
    normalized = _UNSAFE_FILENAME_CHARS.sub("_", normalized)
    suffix = Path(normalized).suffix
    if len(suffix) > 16:
        suffix = ""
    stem = normalized[: -len(suffix)] if suffix else normalized
    return stem[: 120 - len(suffix)] + suffix


def mm_to_emu(mm: float) -> int:
    """Millimeters -> EMU (English Metric Units), the unit python-docx uses internally."""
    return int(mm * 36000)


def emu_to_mm(emu: int | float) -> float:
    return round(emu / 36000, 2)


def emu_to_cm(emu: int | float) -> float:
    return round(emu / 360000, 2)


def cm_to_emu(cm: float) -> int:
    return int(cm * 360000)


def pt_to_emu(pt: float) -> int:
    return int(pt * 12700)


def safe_log_fields(**fields: Any) -> dict[str, Any]:
    """Filter/truncate fields before logging so we never leak document content.

    Any field whose value is a long string is truncated hard; fields named
    like content/body/text are dropped entirely as a defense-in-depth measure.
    """
    banned_keys = {"text", "content", "body", "raw_text", "paragraph_text"}
    clean: dict[str, Any] = {}
    for key, value in fields.items():
        if key.lower() in banned_keys:
            continue
        if isinstance(value, str) and len(value) > 200:
            value = value[:200] + "...[truncated]"
        clean[key] = value
    return clean


def chunked(seq: list[Any], size: int) -> list[list[Any]]:
    return [seq[i : i + size] for i in range(0, len(seq), size)]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
