"""Similarity/plagiarism checking (spec §16).

IMPORTANT: this system does NOT claim to check for plagiarism. No such
mechanism is wired in. This module exists solely as an interface so a real
similarity-detection service (e.g. Antiplagiat, an internal corpus, or an
embeddings-based search) can be plugged in later without touching the rest
of the pipeline. Until an implementation is registered, the bot must never
tell the user their work was checked for plagiarism.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class SimilarityMatch:
    matched_source: str
    similarity_score: float  # 0.0 - 1.0
    matched_excerpt: str
    location_in_document: str


@dataclass
class SimilarityReport:
    overall_similarity_pct: float
    matches: list[SimilarityMatch]


class SimilarityChecker(Protocol):
    """Implement this against a real plagiarism-detection backend to enable
    the feature. No implementation ships with this project."""

    async def check(self, full_text: str) -> SimilarityReport: ...


class UnavailableSimilarityChecker:
    """Default no-op implementation — used until a real checker is configured.
    Deliberately raises rather than silently returning a fake "0% similarity"
    result, so callers can never accidentally present a fabricated result."""

    async def check(self, full_text: str) -> SimilarityReport:
        raise NotImplementedError(
            "No SimilarityChecker is configured for this deployment. "
            "Plagiarism checking is not currently offered to users."
        )
