"""Unicode font registration for PDF reports.

WHY THIS EXISTS: ReportLab's built-in base-14 fonts (Helvetica, Times-Roman,
...) only cover Latin-1 — they have **no Cyrillic glyphs at all**, so any
Russian or Kazakh text rendered with them shows up as black "tofu" boxes.
Kazakh additionally needs glyphs outside plain Russian Cyrillic (Ә Ғ Қ Ң Ө
Ұ Ү Һ І), so the font must cover Cyrillic Extended-A, not just Cyrillic.

We look for a real TTF font that covers both ranges, in order of
preference: an explicit override, common Linux paths (what the Docker
image ships, see Dockerfile), and common Windows paths (for local dev on
Windows, where Arial/Times New Roman already have full Kazakh coverage).
If nothing is found we fall back to Helvetica and log a loud warning —
better a report with the wrong font than a crash.
"""

from __future__ import annotations

import os
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.config.logging import get_logger

logger = get_logger(__name__)

FONT_FAMILY = "DocumentorSans"

# (regular, bold) candidate pairs, checked in order. Bold is optional —
# if missing we reuse the regular face for bold (ReportLab just won't
# actually embolden it, which is a cosmetic downgrade, not a crash).
_CANDIDATES: list[tuple[str, str | None]] = [
    # explicit operator override
    (os.environ.get("PDF_FONT_PATH", ""), os.environ.get("PDF_FONT_PATH_BOLD", "")),
    # Linux / Docker (see Dockerfile: fonts-dejavu-core) — DejaVu Sans
    # covers Cyrillic + Cyrillic Extended-A (Kazakh letters) fully.
    (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ),
    ("/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
    (
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ),
    # Windows — Arial/Times New Roman ship with full Kazakh Cyrillic coverage.
    (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
    (r"C:\Windows\Fonts\times.ttf", r"C:\Windows\Fonts\timesbd.ttf"),
    # macOS
    ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
    (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ),
]

_registered = False
_registered_family = "Helvetica"


def ensure_unicode_font_registered() -> str:
    """Idempotently registers a Cyrillic/Kazakh-capable font and returns the
    ReportLab font family name to use in styles. Safe to call many times."""
    global _registered, _registered_family
    if _registered:
        return _registered_family

    for regular_path, bold_path in _CANDIDATES:
        if not regular_path or not Path(regular_path).exists():
            continue
        try:
            pdfmetrics.registerFont(TTFont(FONT_FAMILY, regular_path))
            bold_ok = bool(bold_path and Path(bold_path).exists())
            if bold_ok:
                pdfmetrics.registerFont(TTFont(f"{FONT_FAMILY}-Bold", bold_path))
            else:
                # Reuse the regular face under the "-Bold" name so styles
                # referencing it don't crash; text just won't look bold.
                pdfmetrics.registerFont(TTFont(f"{FONT_FAMILY}-Bold", regular_path))
            pdfmetrics.registerFontFamily(
                FONT_FAMILY,
                normal=FONT_FAMILY,
                bold=f"{FONT_FAMILY}-Bold",
                italic=FONT_FAMILY,
                boldItalic=f"{FONT_FAMILY}-Bold",
            )
            logger.info("pdf_font_registered", path=regular_path, bold_found=bold_ok)
            _registered_family = FONT_FAMILY
            _registered = True
            return FONT_FAMILY
        except Exception as exc:  # noqa: BLE001
            logger.warning("pdf_font_registration_failed", path=regular_path, error=str(exc))
            continue

    logger.error(
        "pdf_no_unicode_font_found",
        detail=(
            "No Cyrillic/Kazakh-capable TTF font found on this system. "
            "PDF reports will fall back to Helvetica and Cyrillic/Kazakh "
            "text will render as blank boxes. Install fonts-dejavu-core "
            "(Linux) or set PDF_FONT_PATH to a valid .ttf file."
        ),
    )
    _registered_family = "Helvetica"
    _registered = True  # don't retry every call — the warning is enough
    return "Helvetica"
