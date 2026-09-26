"""Resolve direct formatting, style inheritance and OOXML document defaults.

Missing values stay unknown where OOXML provides no default; explicit zero/False
values are never treated as missing. Cyclic user-authored styles are bounded.
"""

from copy import deepcopy
from functools import lru_cache
from types import SimpleNamespace

from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.font import Font
from docx.text.parfmt import ParagraphFormat
from lxml import etree


def style_chain(style):
    visited = set()
    while style is not None and style.style_id not in visited:
        visited.add(style.style_id)
        yield style
        style = style.base_style


def default_element(paragraph, kind):
    root = paragraph.part.document.styles.element
    return root.find(f"{qn('w:docDefaults')}/{qn('w:' + kind + 'Default')}/{qn('w:' + kind)}")


def paragraph_format(paragraph):
    layers = [paragraph.paragraph_format]
    layers.extend(s.paragraph_format for s in style_chain(paragraph.style))
    default = default_element(paragraph, "pPr")
    if default is not None:
        proxy = OxmlElement("w:p")
        proxy.append(deepcopy(default))
        layers.append(ParagraphFormat(proxy))
    properties = (
        "alignment",
        "first_line_indent",
        "left_indent",
        "right_indent",
        "line_spacing",
        "line_spacing_rule",
        "space_before",
        "space_after",
        "page_break_before",
    )
    return SimpleNamespace(
        **{
            key: next((v for layer in layers if (v := getattr(layer, key)) is not None), None)
            for key in properties
        }
    )


def theme_font(paragraph, value):
    group = "majorFont" if value.startswith("major") else "minorFont"
    for rel in paragraph.part.rels.values():
        if rel.reltype.endswith("/theme") and not rel.is_external:
            return _theme_fonts(rel.target_part.blob).get(group)
    return None


def run_font(run, paragraph):
    layers = [run._r.rPr]
    layers += [s.element.rPr for s in style_chain(run.style)]
    layers += [s.element.rPr for s in style_chain(paragraph.style)]
    layers.append(default_element(paragraph, "rPr"))
    values = {k: None for k in ("name", "size", "bold", "italic", "underline")}
    for layer in layers:
        if layer is None:
            continue
        proxy = OxmlElement("w:r")
        proxy.append(deepcopy(layer))
        font = Font(proxy)
        for key in ("size", "bold", "italic", "underline"):
            if values[key] is None:
                values[key] = getattr(font, key)
        if values["name"] is None:
            fonts = layer.find(qn("w:rFonts"))
            if fonts is not None:
                for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
                    themed = fonts.get(qn(f"w:{attr}Theme"))
                    name = theme_font(paragraph, themed) if themed else fonts.get(qn(f"w:{attr}"))
                    if name:
                        values["name"] = name
                        break
    return SimpleNamespace(**values)


@lru_cache(maxsize=32)
def _theme_fonts(blob):
    tree = etree.fromstring(blob, etree.XMLParser(resolve_entities=False, no_network=True))
    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    result = {}
    for group in ("majorFont", "minorFont"):
        node = tree.find(f".//a:{group}/a:latin", ns)
        if node is not None:
            result[group] = node.get("typeface") or None
    return result
