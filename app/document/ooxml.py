"""Low-level OOXML access.

python-docx covers most needs, but a few things it does not expose cleanly
(e.g. section-level header/footer presence flags, some numbering details).
For those we fall back to raw XML access via the zipfile + lxml, per the
project spec (§3 Word).
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from lxml import etree

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def read_part(docx_path: Path, part_name: str) -> bytes | None:
    with zipfile.ZipFile(docx_path) as zf:
        if part_name not in zf.namelist():
            return None
        return zf.read(part_name)


def get_document_xml_tree(docx_path: Path) -> etree._Element:
    data = read_part(docx_path, "word/document.xml")
    if data is None:
        raise FileNotFoundError("word/document.xml not found in archive")
    return etree.fromstring(data, etree.XMLParser(resolve_entities=False, no_network=True))


def section_has_header_footer(docx_path: Path) -> tuple[bool, bool]:
    """Return (has_header, has_footer) based on sectPr references."""
    tree = get_document_xml_tree(docx_path)
    has_header = bool(tree.findall(".//w:headerReference", NS))
    has_footer = bool(tree.findall(".//w:footerReference", NS))
    return has_header, has_footer


def list_embedded_fonts(docx_path: Path) -> set[str]:
    """Collect every distinct font name referenced anywhere in the document,
    including inside rFonts elements which python-docx sometimes misses
    for complex-script / east-asian font attributes."""
    tree = get_document_xml_tree(docx_path)
    fonts: set[str] = set()
    for el in tree.findall(".//w:rFonts", NS):
        for attr in ("{%s}ascii" % NS["w"], "{%s}hAnsi" % NS["w"], "{%s}cs" % NS["w"]):
            val = el.get(attr)
            if val:
                fonts.add(val)
    return fonts


def count_content_parts(docx_path: Path) -> dict:
    """Sanity-check archive contents (used by the security/format validators
    and diagnostics), returning counts of key part types."""
    with zipfile.ZipFile(docx_path) as zf:
        names = zf.namelist()
    return {
        "total_parts": len(names),
        "has_document": "word/document.xml" in names,
        "has_styles": "word/styles.xml" in names,
        "has_numbering": "word/numbering.xml" in names,
        "image_parts": len([n for n in names if n.startswith("word/media/")]),
    }
