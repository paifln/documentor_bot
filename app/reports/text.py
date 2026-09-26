"""Plain text to safe PDF markup, with explicit unsupported glyph notation."""

import unicodedata
from xml.sax.saxutils import escape

from reportlab.pdfbase import pdfmetrics

from app.reports.fonts import ensure_unicode_font_registered


def pdf_text(value: str) -> str:
    family = ensure_unicode_font_registered()
    # Use the intersection because text may appear inside a bold span.
    regular = pdfmetrics.getFont(family).face.charToGlyph
    bold = pdfmetrics.getFont(f"{family}-Bold").face.charToGlyph
    cleaned = []
    for char in unicodedata.normalize("NFC", value):
        if char in "\n\r\t":
            cleaned.append(" ")
        elif unicodedata.category(char) in {"Cc", "Cf"} or char in "\ufe0e\ufe0f":
            continue
        elif ord(char) in regular and ord(char) in bold:
            cleaned.append(char)
        else:
            cleaned.append(f"[U+{ord(char):04X}]")
    return escape("".join(cleaned))
