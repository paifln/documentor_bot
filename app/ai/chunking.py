"""Chunking of long documents before AI analysis (spec §14/§28).

We never send the whole document in one request. Instead:
  DOCX -> section text (from app.document.structure) -> chunks here.

A simple word-count-based estimate stands in for a real tokenizer, which
keeps this provider-agnostic (different vendors tokenize differently) at
the cost of being approximate — the margin built into MAX_AI_TOKENS_PER_CHECK
absorbs that imprecision.
"""

from __future__ import annotations

from dataclasses import dataclass

_WORDS_PER_TOKEN_ESTIMATE = 0.75  # ~1 token per 0.75 Russian words, rough heuristic
_DEFAULT_MAX_WORDS_PER_CHUNK = 900  # ≈ 1200 tokens, leaves room for prompt + response


@dataclass
class TextChunk:
    section_key: str
    chunk_index: int
    text: str
    word_count: int


def estimate_tokens(text: str) -> int:
    words = len(text.split())
    return int(words / _WORDS_PER_TOKEN_ESTIMATE)


def chunk_section(
    section_key: str, text: str, max_words: int = _DEFAULT_MAX_WORDS_PER_CHUNK
) -> list[TextChunk]:
    words = text.split()
    if len(words) <= max_words:
        return [TextChunk(section_key, 0, text, len(words))] if text.strip() else []

    chunks: list[TextChunk] = []
    for i in range(0, len(words), max_words):
        piece_words = words[i : i + max_words]
        chunks.append(
            TextChunk(
                section_key=section_key,
                chunk_index=i // max_words,
                text=" ".join(piece_words),
                word_count=len(piece_words),
            )
        )
    return chunks


def chunk_sections(
    sections: dict[str, str], max_words: int = _DEFAULT_MAX_WORDS_PER_CHUNK
) -> list[TextChunk]:
    all_chunks: list[TextChunk] = []
    for key, text in sections.items():
        if not text.strip():
            continue
        all_chunks.extend(chunk_section(key, text, max_words))
    return all_chunks


def total_estimated_tokens(chunks: list[TextChunk]) -> int:
    return sum(estimate_tokens(c.text) for c in chunks)


def cap_chunks_to_budget(chunks: list[TextChunk], max_tokens_budget: int) -> list[TextChunk]:
    """Drop the least-essential chunks (large body-text tail chunks first)
    if the estimated total would exceed the configured per-check AI budget.
    Introduction/conclusion/references are prioritized since they carry the
    most structurally-important content."""
    priority_order = {"introduction": 0, "conclusion": 1, "abstract": 2}

    def sort_key(c: TextChunk) -> tuple[int, int]:
        return (priority_order.get(c.section_key, 5), c.chunk_index)

    ordered = sorted(chunks, key=sort_key)
    kept: list[TextChunk] = []
    used_tokens = 0
    for c in ordered:
        cost = estimate_tokens(c.text)
        if used_tokens + cost > max_tokens_budget:
            continue
        kept.append(c)
        used_tokens += cost
    return kept
