import json
import asyncio

import pytest

from app.ai.analyzer import AIAnalyzer
from app.ai.provider import LLMProvider, LLMResponse
from app.analysis.aggregator import aggregate
from app.common.exceptions import AIProviderError
from app.config.settings import Settings
from app.document.labels import display_location, section_label
from app.reports.generator import build_results_message


class SequenceProvider(LLMProvider):
    name = "test"

    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = 0
        self.prompts = []

    async def complete(self, **kwargs):
        self.calls += 1
        self.prompts.append(kwargs["user_prompt"])
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        text = response if isinstance(response, str) else json.dumps(response)
        return LLMResponse(text, "test", input_tokens=100, output_tokens=50)


def response(categories=("language", "style", "content")):
    return {"evaluated_categories": list(categories), "errors": []}


@pytest.mark.asyncio
async def test_combined_review_uses_one_request_per_chunk():
    provider = SequenceProvider([response(), response()])
    outcome = await AIAnalyzer(provider, Settings(_env_file=None)).analyze_document(
        {"body": "word " * 1200}
    )
    assert outcome.complete
    assert provider.calls == 2  # previously six requests for the same text
    assert outcome.tokens_used == 300
    assert all("Раздел: Основная часть" in prompt for prompt in provider.prompts)


@pytest.mark.asyncio
async def test_partial_success_survives_another_category_failure(sample_preset):
    provider = SequenceProvider([response(), response(("language",))])
    outcome = await AIAnalyzer(provider, Settings(_env_file=None)).analyze_document(
        {"body": "word " * 1200}
    )
    assert outcome.category_coverage == {"language": 1, "style": 0.5, "content": 0.5}
    result = aggregate(
        [], [], sample_preset, {}, outcome.complete, ai_category_coverage=outcome.category_coverage
    )
    assert result.provisional
    assert result.max_score == 100
    assert all(c.evaluated for c in result.category_scores)
    assert "50%" in build_results_message(result)


@pytest.mark.asyncio
async def test_failed_chunk_does_not_erase_successful_review(sample_preset):
    provider = SequenceProvider([response(), AIProviderError("unavailable")])
    settings = Settings(_env_file=None, LLM_MAX_RETRIES=1)
    outcome = await AIAnalyzer(provider, settings).analyze_document({"body": "word " * 1200})
    assert outcome.coverage == 0.5
    assert outcome.failure_reasons == ["provider"]
    result = aggregate(
        [], [], sample_preset, {}, False, ai_category_coverage=outcome.category_coverage
    )
    assert all(c.evaluated for c in result.category_scores)


@pytest.mark.asyncio
async def test_invalid_json_usage_is_settled_before_retry():
    provider = SequenceProvider(['{"errors":', response()])
    settings = Settings(_env_file=None, MAX_AI_TOKENS_PER_CHECK=7000, LLM_MAX_RETRIES=2)
    outcome = await AIAnalyzer(provider, settings).analyze_document({"body": "Short text"})
    assert outcome.complete
    assert provider.calls == 2
    assert outcome.tokens_used == 300


@pytest.mark.asyncio
async def test_budget_exhaustion_is_explained_without_provider_call():
    provider = SequenceProvider([])
    settings = Settings(_env_file=None, MAX_AI_TOKENS_PER_CHECK=100)
    outcome = await AIAnalyzer(provider, settings).analyze_document({"body": "Short text"})
    assert outcome.failure_reasons == ["budget"]
    assert outcome.coverage == 0
    assert provider.calls == 0


def test_parser_keys_are_not_user_facing():
    assert (
        section_label("unnamed:63", "1. Цифровизация образования\nТекст")
        == "1. Цифровизация образования"
    )
    value = display_location("unnamed:63, body, Section 2")
    assert value == "Абзац 64, Основная часть, Раздел 2"
    for lang in ("ru", "kk", "en"):
        assert "unnamed" not in section_label("unnamed63", lang=lang)
        assert section_label("content_table", lang=lang) != "section.content_table"


def test_incomplete_score_is_normalized_and_explicit(sample_preset):
    result = aggregate([], [], sample_preset, {}, False)
    assert result.score == result.max_score == 100
    assert result.evaluated_max_score == 50
    assert result.provisional
    assert "Предварительный" in build_results_message(result)
    assert all(c.earned_points == 0 for c in result.category_scores if not c.evaluated)


@pytest.mark.asyncio
async def test_missing_category_confirmation_is_not_full_marks():
    provider = SequenceProvider([{"errors": []}])
    outcome = await AIAnalyzer(
        provider, Settings(_env_file=None, LLM_MAX_RETRIES=1)
    ).analyze_document({"body": "Short text"})
    assert not outcome.complete
    assert outcome.coverage == 0
    assert outcome.failure_reasons == ["invalid_response"]


@pytest.mark.asyncio
async def test_deadline_returns_partial_result_instead_of_losing_document():
    class SlowProvider(LLMProvider):
        name = "slow"

        async def complete(self, **kwargs):
            await asyncio.sleep(5)
            return LLMResponse(json.dumps(response()), "test")

    settings = Settings(_env_file=None, LLM_ANALYSIS_TIMEOUT_SECONDS=1)
    outcome = await AIAnalyzer(SlowProvider(), settings).analyze_document({"body": "Short text"})
    assert outcome.failure_reasons == ["timeout"]
    assert outcome.coverage == 0


def test_legacy_scale_is_normalized_without_changing_saved_result():
    from app.common.models import CheckResult, CheckSummary
    from app.reports.presentation import score_over_100, score_note

    result = CheckResult(
        score=34, max_score=50, summary=CheckSummary(), ai_analysis_available=False
    )
    assert score_over_100(result) == 68
    assert result.score == 34 and result.max_score == 50
    assert "Предварительный" in score_note(result, "ru")
