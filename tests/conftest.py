from __future__ import annotations

import pytest

from app.rules.models import (
    FontRule,
    HeadingsRule,
    MarginsRule,
    PageRule,
    ParagraphRule,
    ReferencesRule,
    RulePreset,
    ScoringWeights,
    StructureRule,
)
from tests.fixtures import generate_test_docs as gen


@pytest.fixture(scope="session")
def correct_docx():
    return gen.build_correct()


@pytest.fixture(scope="session")
def wrong_font_docx():
    return gen.build_wrong_font()


@pytest.fixture(scope="session")
def wrong_margins_docx():
    return gen.build_wrong_margins()


@pytest.fixture(scope="session")
def wrong_spacing_docx():
    return gen.build_wrong_spacing()


@pytest.fixture(scope="session")
def missing_sections_docx():
    return gen.build_missing_sections()


@pytest.fixture(scope="session")
def mixed_formatting_docx():
    return gen.build_mixed_formatting()


@pytest.fixture
def sample_preset() -> RulePreset:
    return RulePreset(
        id="test_preset",
        name="Test Preset",
        institution="Test University",
        work_type="coursework",
        margins=MarginsRule(top_mm=20, bottom_mm=20, left_mm=30, right_mm=10),
        font=FontRule(name="Times New Roman", size_pt=14),
        paragraph=ParagraphRule(),
        headings=HeadingsRule(),
        structure=StructureRule(
            required_sections=[
                "introduction",
                "theoretical_part",
                "practical_part",
                "conclusion",
                "references",
            ]
        ),
        references=ReferencesRule(min_sources=10),
        scoring=ScoringWeights(),
    )
