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
    usage = {}
    for paragraph in body_paragraphs(document):
        for run in paragraph.runs:
            if run.text.strip():
                key = (run.font_name, run.font_size_pt)
                usage[key] = usage.get(key, 0) + len(run.text)
    total = sum(usage.values()) or 1
    stats = [
        FontUsageStat(
            name=name,
            size_pt=size,
            char_count=count,
            percentage=round(count / total * 100, 1),
        )
        for (name, size), count in usage.items()
    ]
    return sorted(stats, key=lambda s: s.char_count, reverse=True)


def body_paragraphs(document: ParsedDocument) -> list[ParagraphInfo]:
    """Paragraphs that represent normal body text (not headings, not empty)."""
    from app.document.structure import analyze_structure

    structure = analyze_structure(document)
    references = structure.detected_sections.get("references")
    first = min((h.paragraph_index for h in structure.headings), default=0)
    return [
        p
        for p in document.paragraphs
        if not p.is_heading
        and not p.is_empty
        and not p.in_table
        and p.index >= first
        and not p.is_numbered
        and (references is None or p.index < references.paragraph_index)
        and p.style_name.lower() not in {"title", "subtitle", "caption", "toc 1", "toc 2"}
    ]


def heading_paragraphs(document: ParsedDocument) -> list[ParagraphInfo]:
    return [p for p in document.paragraphs if p.is_heading]
