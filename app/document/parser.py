"""DOCX -> structural document model.

This is the single source of truth used by both the Rule Engine and the
AI analysis pipeline. Parsing happens exactly once per check.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import docx
from docx.document import Document as DocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.common.exceptions import CorruptedDocumentError, TextExtractionError
from app.common.utils import emu_to_cm, emu_to_mm
from app.document import ooxml
from app.document.effective import paragraph_format, run_font, style_chain

# Matches localized *displayed* names of Word's built-in heading styles.
# Used only as a last-resort fallback (see _paragraph_outline_level) — the
# w:outlineLvl / style_id checks above cover the vast majority of real
# documents regardless of the Word UI language they were authored in.
_HEADING_STYLE_NAME_PATTERNS = [
    r"^heading\s*0*([1-9])$",  # English: "Heading 1"
    r"^заголовок\s*0*([1-9])$",  # Russian: "Заголовок 1"
    r"^тақырып\s*0*([1-9])$",  # Kazakh: "Тақырып 1"
    r"^такырып\s*0*([1-9])$",  # Kazakh, no diacritics (some templates)
]

_ALIGNMENT_MAP = {
    WD_ALIGN_PARAGRAPH.LEFT: "left",
    WD_ALIGN_PARAGRAPH.RIGHT: "right",
    WD_ALIGN_PARAGRAPH.CENTER: "center",
    WD_ALIGN_PARAGRAPH.JUSTIFY: "justify",
    None: "left",  # inherited/default
}


@dataclass
class RunInfo:
    text: str
    font_name: str | None
    font_size_pt: float | None
    bold: bool
    italic: bool
    underline: bool
    color_rgb: str | None


@dataclass
class ParagraphInfo:
    index: int
    text: str
    style_name: str
    outline_level: int | None  # 0 = Heading 1, None = body text
    alignment: str
    line_spacing: float | None
    line_spacing_rule: str | None
    space_before_pt: float | None
    space_after_pt: float | None
    first_line_indent_cm: float | None
    left_indent_cm: float | None
    right_indent_cm: float | None
    runs: list[RunInfo] = field(default_factory=list)
    in_table: bool = False
    page_break_before: bool = False
    is_numbered: bool = False

    @property
    def is_heading(self) -> bool:
        return self.outline_level is not None and self.outline_level < 9

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()

    @property
    def dominant_font(self) -> tuple[str | None, float | None]:
        """Best-effort dominant (name, size) among this paragraph's runs,
        weighted by run text length."""
        if not self.runs:
            return None, None
        weighted: dict[tuple[str | None, float | None], int] = {}
        for r in self.runs:
            key = (r.font_name, r.font_size_pt)
            weighted[key] = weighted.get(key, 0) + max(len(r.text), 1)
        return max(weighted.items(), key=lambda kv: kv[1])[0]


@dataclass
class SectionPageInfo:
    page_width_mm: float
    page_height_mm: float
    orientation: str
    margin_top_mm: float
    margin_bottom_mm: float
    margin_left_mm: float
    margin_right_mm: float
    header_distance_mm: float
    footer_distance_mm: float


@dataclass
class ParsedDocument:
    path: Path
    paragraphs: list[ParagraphInfo]
    page: SectionPageInfo
    has_header: bool
    has_footer: bool
    table_count: int
    image_count: int
    font_usage: dict[tuple[str | None, float | None], int]  # (name, size) -> char count
    estimated_page_count: int
    pages: list[SectionPageInfo] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n".join(p.text for p in self.paragraphs if p.text.strip())

    @property
    def dominant_font(self) -> tuple[str | None, float | None] | None:
        if not self.font_usage:
            return None
        return max(self.font_usage.items(), key=lambda kv: kv[1])[0]


def _run_color(run) -> str | None:
    try:
        color = run.font.color
        if color and color.type is not None and color.rgb is not None:
            return str(color.rgb)
    except Exception:  # noqa: BLE001 - defensive: python-docx can raise on odd XML
        return None
    return None


def _paragraph_outline_level(paragraph) -> int | None:
    """Heading level detection — must work regardless of the Word UI
    language the document was authored in (Kazakh/Russian/English Word all
    produce different *display* style names: "Heading 1" / "Заголовок 1" /
    "Тақырып 1", but the underlying OOXML is language-independent).

    Priority order (most to least reliable):
      1. Explicit w:outlineLvl override in pPr — always present regardless
         of language, set automatically whenever a heading style is applied.
      2. The style's internal style_id (w:styleId), which for Word's built-in
         heading styles is always "Heading1".."Heading9" in the XML itself,
         even when the *displayed* style name is localized.
      3. Multilingual pattern match against the displayed style name, as a
         last resort for custom/renamed styles.
    """
    ppr = paragraph._p.pPr
    if ppr is not None:
        outline_el = ppr.find(qn("w:outlineLvl"))
        if outline_el is not None:
            val = outline_el.get(qn("w:val"))
            if val is not None:
                return int(val)

    for inherited in style_chain(paragraph.style):
        props = inherited.element.pPr
        outline = props.find(qn("w:outlineLvl")) if props is not None else None
        if outline is not None:
            return int(outline.get(qn("w:val")))
    style = paragraph.style
    if style is not None:
        style_id = getattr(style, "style_id", None) or ""
        match = re.match(r"(?i)^heading0*([1-9])$", style_id.replace(" ", ""))
        if match:
            return int(match.group(1)) - 1

        style_name = (style.name or "").strip().lower()
        for pattern in _HEADING_STYLE_NAME_PATTERNS:
            m = re.match(pattern, style_name)
            if m and m.group(1):
                return int(m.group(1)) - 1
            if m:
                return 0
    return None


def _spacing_pt(value) -> float | None:
    if value is None:
        return None
    return round(value.pt, 2)


def _line_spacing(paragraph) -> tuple[float | None, str | None]:
    pf = paragraph_format(paragraph)
    rule = pf.line_spacing_rule
    if pf.line_spacing is None:
        return 1.0, "SINGLE"
    # For MULTIPLE rule, line_spacing is a float multiplier (e.g. 1.5).
    # For EXACT/AT_LEAST it's a Length; normalize to points in that case.
    if hasattr(pf.line_spacing, "pt"):
        return round(pf.line_spacing.pt, 2), str(rule) if rule is not None else None
    return float(pf.line_spacing), str(rule) if rule is not None else None


def _parse_paragraph(paragraph, index: int, in_table: bool = False) -> ParagraphInfo:
    pf = paragraph_format(paragraph)
    line_spacing, line_spacing_rule = _line_spacing(paragraph)

    runs = [
        RunInfo(
            text=r.text,
            font_name=font.name,
            font_size_pt=(font.size.pt if font.size is not None else None),
            bold=bool(font.bold),
            italic=bool(font.italic),
            underline=bool(font.underline),
            color_rgb=_run_color(r),
        )
        for r in paragraph.runs
        for font in [run_font(r, paragraph)]
    ]

    return ParagraphInfo(
        index=index,
        text=paragraph.text,
        style_name=paragraph.style.name if paragraph.style else "Normal",
        outline_level=_paragraph_outline_level(paragraph),
        alignment=_ALIGNMENT_MAP.get(pf.alignment, "left"),
        line_spacing=line_spacing,
        line_spacing_rule=line_spacing_rule,
        space_before_pt=_spacing_pt(pf.space_before),
        space_after_pt=_spacing_pt(pf.space_after),
        first_line_indent_cm=(emu_to_cm(pf.first_line_indent) if pf.first_line_indent else None),
        left_indent_cm=(emu_to_cm(pf.left_indent) if pf.left_indent else None),
        right_indent_cm=(emu_to_cm(pf.right_indent) if pf.right_indent else None),
        runs=runs,
        in_table=in_table,
        page_break_before=bool(pf.page_break_before),
        is_numbered=any(
            x is not None and x.find(qn("w:numPr")) is not None
            for x in [paragraph._p.pPr, *[st.element.pPr for st in style_chain(paragraph.style)]]
        ),
    )


def _parse_page_info(section) -> SectionPageInfo:
    orientation = "landscape" if section.orientation == 1 else "portrait"
    return SectionPageInfo(
        page_width_mm=emu_to_mm(section.page_width),
        page_height_mm=emu_to_mm(section.page_height),
        orientation=orientation,
        margin_top_mm=emu_to_mm(section.top_margin),
        margin_bottom_mm=emu_to_mm(section.bottom_margin),
        margin_left_mm=emu_to_mm(section.left_margin),
        margin_right_mm=emu_to_mm(section.right_margin),
        header_distance_mm=emu_to_mm(section.header_distance or 0),
        footer_distance_mm=emu_to_mm(section.footer_distance or 0),
    )


def _estimate_page_count(paragraphs: list[ParagraphInfo], chars_per_page: int = 2200) -> int:
    """Heuristic page estimate (no real page layout engine available headlessly).
    Used only for soft limits / progress reporting, never for scoring."""
    total_chars = sum(len(p.text) for p in paragraphs)
    return max(1, round(total_chars / chars_per_page))


def parse_docx(path: Path) -> ParsedDocument:
    try:
        document = docx.Document(str(path))
    except Exception as exc:  # noqa: BLE001
        raise CorruptedDocumentError(f"python-docx failed to open file: {exc}") from exc

    try:
        paragraphs = []
        previous_break = False
        for element in document.element.body.iter(qn("w:p")):
            in_table = any(a.tag == qn("w:tc") for a in element.iterancestors())
            paragraph = _parse_paragraph(Paragraph(element, document), len(paragraphs), in_table)
            paragraph.page_break_before |= previous_break
            previous_break = bool(element.xpath('.//w:br[@w:type="page"]'))
            paragraphs.append(paragraph)
    except Exception as exc:  # noqa: BLE001
        raise TextExtractionError(f"failed extracting paragraphs: {exc}") from exc

    if not any(p.text.strip() for p in paragraphs):
        raise TextExtractionError("document contains no extractable text")

    pages = [_parse_page_info(section) for section in document.sections]
    page = pages[0]

    try:
        has_header, has_footer = ooxml.section_has_header_footer(path)
    except Exception:  # noqa: BLE001
        has_header, has_footer = False, False

    table_count = len(document.tables)
    image_count = _count_images(document)

    font_usage: dict[tuple[str | None, float | None], int] = {}
    for p in paragraphs:
        for r in p.runs:
            key = (r.font_name, r.font_size_pt)
            font_usage[key] = font_usage.get(key, 0) + max(len(r.text), 0)

    return ParsedDocument(
        path=path,
        paragraphs=paragraphs,
        page=page,
        pages=pages,
        has_header=has_header,
        has_footer=has_footer,
        table_count=table_count,
        image_count=image_count,
        font_usage=font_usage,
        estimated_page_count=_estimate_page_count(paragraphs),
    )


def _count_images(document: DocxDocument) -> int:
    try:
        return len(document.inline_shapes)
    except Exception:  # noqa: BLE001
        return 0


def iter_tables(document_path: Path) -> list[Table]:
    document = docx.Document(str(document_path))
    return list(document.tables)
