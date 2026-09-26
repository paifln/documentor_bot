"""Detects the logical structure of the coursework: headings and the
canonical sections they correspond to (Введение, Заключение, etc.).

This module is pure Python pattern matching over the parsed document —
no AI involved, per spec §9/§10 ("технический структуру документа
проверять обычным кодом").
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.document.parser import ParagraphInfo, ParsedDocument

# Canonical section keys -> regex patterns that match a heading naming them.
# Patterns are intentionally tolerant of numbering prefixes ("1 ", "1.", "I.")
# and common spelling variants, and cover Russian, Kazakh and English —
# Documentor serves Makhambet University, where all three are common.
_SECTION_PATTERNS: dict[str, list[str]] = {
    "introduction": [
        r"введение",
        r"кіріспе",
        r"^introduction$",
    ],
    "theoretical_part": [
        r"теоретическ\w*\s+част",
        r"глава\s*1\b",
        r"теоретическ\w*\s+обзор",
        r"теориялық\s+бөлім",
        r"әдебиеттерге\s+шолу",
        r"theoretical\s+part",
        r"literature\s+review",
        r"^chapter\s*1\b",
    ],
    "practical_part": [
        r"практическ\w*\s+част",
        r"глава\s*2\b",
        r"экспериментальн\w*\s+част",
        r"практикалық\s+бөлім",
        r"тәжірибелік\s+бөлім",
        r"practical\s+part",
        r"experimental\s+part",
        r"^chapter\s*2\b",
    ],
    "main_body": [
        r"основн\w*\s+част",
        r"негізгі\s+бөлім",
        r"^main\s+(part|body)$",
        r"^body$",
    ],
    "conclusion": [
        r"заключение",
        r"выводы",
        r"қорытынды",
        r"^conclusion(s)?$",
    ],
    "references": [
        r"список\s+(использованн\w*\s+)?(литератур\w*|источник\w*)",
        r"библиограф",
        r"пайдаланылған\s+әдебиеттер",
        r"әдебиеттер\s+тізімі",
        r"^references$",
        r"^bibliography$",
        r"^list\s+of\s+references$",
    ],
    "appendix": [
        r"приложени",
        r"қосымша",
        r"^appendi(x|ces)$",
    ],
    "abstract": [
        r"^аннотаци",
        r"^реферат\b",
        r"^аңдатпа",
        r"^түйін\b",
        r"^abstract$",
    ],
    "content_table": [
        r"^содержание$",
        r"^оглавление$",
        r"^мазмұны$",
        r"^contents$",
        r"^table\s+of\s+contents$",
    ],
}

_HEADING_NUMBER_PREFIX = re.compile(r"^\s*(\d+(\.\d+)*\.?|[IVXLC]+\.)\s*")


@dataclass
class DetectedHeading:
    paragraph_index: int
    raw_text: str
    normalized_text: str
    level: int
    section_key: str | None
    numbering: str | None


@dataclass
class StructureReport:
    headings: list[DetectedHeading]
    detected_sections: dict[str, DetectedHeading]  # section_key -> heading
    numbering_error_pairs: list[tuple[int, int]]  # (prev_number, curr_number)
    level_error_details: list[tuple[str, int, int]]  # (heading_text, prev_level, curr_level)

    @property
    def numbering_errors(self) -> list[tuple[int, int]]:
        return self.numbering_error_pairs

    @property
    def level_errors(self) -> list[tuple[str, int, int]]:
        return self.level_error_details


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _extract_numbering(text: str) -> str | None:
    match = _HEADING_NUMBER_PREFIX.match(text)
    return match.group(1).rstrip(".") if match else None


def _match_section_key(normalized: str) -> str | None:
    stripped = _HEADING_NUMBER_PREFIX.sub("", normalized).strip()
    for key, patterns in _SECTION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, stripped):
                return key
    return None


def detect_headings(paragraphs: list[ParagraphInfo]) -> list[DetectedHeading]:
    headings: list[DetectedHeading] = []
    for p in paragraphs:
        if not p.is_heading or p.is_empty:
            continue
        normalized = _normalize(p.text)
        headings.append(
            DetectedHeading(
                paragraph_index=p.index,
                raw_text=p.text.strip(),
                normalized_text=normalized,
                level=(p.outline_level or 0) + 1,
                section_key=_match_section_key(normalized),
                numbering=_extract_numbering(p.text.strip()) or ("auto" if p.is_numbered else None),
            )
        )
    return headings


def _check_numbering_sequence(headings: list[DetectedHeading]) -> list[tuple[int, int]]:
    """Very lightweight sanity check: top-level numbers should be
    monotonically increasing integers starting at 1 (when numbering is used
    at all). We deliberately keep this permissive — many valid documents
    number only some heading levels.
    """
    errors: list[tuple[int, int]] = []
    top_level_numbers: list[int] = []
    for h in headings:
        if h.level == 1 and h.numbering and h.numbering.isdigit():
            top_level_numbers.append(int(h.numbering))

    for i in range(1, len(top_level_numbers)):
        if top_level_numbers[i] != top_level_numbers[i - 1] + 1:
            errors.append((top_level_numbers[i - 1], top_level_numbers[i]))
    return errors


def _check_level_consistency(headings: list[DetectedHeading]) -> list[tuple[str, int, int]]:
    """Flag a heading that jumps more than one level deeper than its
    predecessor (e.g. Heading 1 directly followed by Heading 3)."""
    errors: list[tuple[str, int, int]] = []
    prev_level = 0
    for h in headings:
        if h.level - prev_level > 1:
            errors.append((h.raw_text, prev_level, h.level))
        prev_level = h.level
    return errors


def analyze_structure(document: ParsedDocument) -> StructureReport:
    headings = detect_headings(document.paragraphs)

    detected_sections: dict[str, DetectedHeading] = {}
    for h in headings:
        if h.section_key and h.section_key not in detected_sections:
            detected_sections[h.section_key] = h

    return StructureReport(
        headings=headings,
        detected_sections=detected_sections,
        numbering_error_pairs=_check_numbering_sequence(headings),
        level_error_details=_check_level_consistency(headings),
    )


def split_into_logical_sections(
    document: ParsedDocument, structure: StructureReport
) -> dict[str, str]:
    """Slice the full paragraph list into text blocks per detected section,
    keyed by section_key. Used by app/ai/chunking.py so the AI never has to
    receive the whole document in one request (spec §14)."""
    ordered = sorted(structure.headings, key=lambda h: h.paragraph_index)
    boundaries: list[tuple[int, str]] = [
        (h.paragraph_index, h.section_key or f"unnamed:{h.paragraph_index}")
        for h in ordered
        if h.section_key or h.level == 1
    ]

    if not boundaries or boundaries[0][0] > 0:
        boundaries.insert(0, (0, "body"))

    sections: dict[str, str] = {}
    for i, (start_idx, key) in enumerate(boundaries):
        end_idx = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(document.paragraphs)
        text = "\n".join(p.text for p in document.paragraphs[start_idx:end_idx] if p.text.strip())
        if key in sections:
            sections[key] += "\n" + text
        else:
            sections[key] = text
    return sections
