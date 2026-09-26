from __future__ import annotations

import pytest

from app.ai.analyzer import AIAnalyzer, PromptLibrary
from app.ai.provider import MockProvider
from app.analysis.pipeline import AnalysisPipeline
from app.config.settings import get_settings
from app.rules.engine import RuleEngine


@pytest.mark.asyncio
async def test_full_pipeline_correct_document(correct_docx, sample_preset):
    settings = get_settings()
    analyzer = AIAnalyzer(MockProvider(), settings, PromptLibrary(settings.prompts_dir))
    pipeline = AnalysisPipeline(RuleEngine(), analyzer)

    seen_stages: list[str] = []

    async def on_progress(stage: str) -> None:
        seen_stages.append(stage)

    result = await pipeline.run(correct_docx, sample_preset, on_progress=on_progress)

    assert result.score > 0
    assert result.max_score == 50.0  # offline mock leaves AI categories unevaluated
    assert result.ai_analysis_available is False
    assert seen_stages == ["structure", "formatting", "text", "ai", "report"]
    assert any(f.rule_id == "font.main" for f in result.findings)


@pytest.mark.asyncio
async def test_full_pipeline_missing_sections_scores_lower_than_correct(
    correct_docx, missing_sections_docx, sample_preset
):
    settings = get_settings()
    analyzer = AIAnalyzer(MockProvider(), settings, PromptLibrary(settings.prompts_dir))
    pipeline = AnalysisPipeline(RuleEngine(), analyzer)

    good_result = await pipeline.run(correct_docx, sample_preset)
    bad_result = await pipeline.run(missing_sections_docx, sample_preset)

    assert bad_result.score < good_result.score
    assert bad_result.summary.critical > 0
