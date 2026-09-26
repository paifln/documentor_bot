"""Human-facing section names; parser identifiers never leave this boundary."""

import re

from app.i18n import t

_SECTIONS = {
    "introduction",
    "theoretical_part",
    "practical_part",
    "main_body",
    "conclusion",
    "references",
    "appendix",
    "abstract",
    "content_table",
}


def section_label(key: str, text: str = "", lang: str = "ru") -> str:
    if key in _SECTIONS:
        return t(f"section.{key}", lang)
    if key.startswith("unnamed"):
        title = text.splitlines()[0].strip() if text.strip() else ""
        if title and len(title) <= 180:
            return title
        number = re.search(r"\d+", key)
        return (
            t("location.paragraph", lang, n=int(number[0]) + 1)
            if number
            else t("section.main_body", lang)
        )
    return t("section.main_body", lang)


def display_location(value: str, lang: str = "ru") -> str:
    """Also sanitizes locations in older, already persisted reports."""
    value = re.sub(
        r"\bunnamed:?\s*(\d+)\b", lambda m: t("location.paragraph", lang, n=int(m[1]) + 1), value
    )
    value = re.sub(r"\b(body|main_body)\b", t("section.main_body", lang), value)
    value = re.sub(r"\bSection\s+(\d+)", lambda m: t("location.section", lang, n=m[1]), value)
    for key in _SECTIONS:
        value = re.sub(rf"\b{key}\b", t(f"section.{key}", lang), value)
    return value
