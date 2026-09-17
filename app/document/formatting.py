"""Aggregated formatting statistics used by the rule validators.

Keeping this separate from parser.py means validators work against small,
purpose-built summaries rather than re-walking the raw python-docx tree
each time.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.document.parser import ParagraphInfo, ParsedDocument


@dataclass
class FontUsageStat:
    name: str | None
    size_pt: float | None
    char_count: int
    percentage: float


def font_usage_breakdown(document: ParsedDocument) -> list[FontUsageStat]:
    total = sum(document.font_usage.values()) or 1
    stats = [
        FontUsageStat(
            name=name,
            size_pt=size,
            char_count=count,
            percentage=round(count / total * 100, 1),
        )
        for (name, size), count in document.font_usage.items()
    ]
    return sorted(stats, key=lambda s: s.char_count, reverse=True)


def body_paragraphs(document: ParsedDocument) -> list[ParagraphInfo]:
    """Paragraphs that represent normal body text (not headings, not empty)."""
    return [p for p in document.paragraphs if not p.is_heading and not p.is_empty]


def heading_paragraphs(document: ParsedDocument) -> list[ParagraphInfo]:
    return [p for p in document.paragraphs if p.is_heading]
