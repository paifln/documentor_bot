from __future__ import annotations

import json

import pytest

from app.ai.analyzer import AIAnalyzer, PromptLibrary
from app.ai.provider import LLMProvider, LLMResponse
from app.ai.schemas import AIError, AIErrorList
from app.config.settings import get_settings


def test_ai_error_schema_clamps_unknown_category():
    err = AIError(category="nonsense", severity="warning", explanation="x")
    assert err.category == "content"


def test_ai_error_schema_truncates_long_quote():
    err = AIError(category="style", severity="info", explanation="x", original_text="a" * 500)
    assert len(err.original_text) == 200


def test_ai_error_list_parses_valid_json():
    raw = {
        "errors": [
            {
                "category": "language",
                "severity": "warning",
                "location": "абзац 1",
                "original_text": "пример текста",
                "explanation": "ошибка",
                "suggestion": "исправление",
                "confidence": 0.9,
            }
        ]
    }
    parsed = AIErrorList.model_validate(raw)
    assert len(parsed.errors) == 1
    assert parsed.errors[0].confidence == 0.9


class _StubProvider(LLMProvider):
    name = "stub"

    def __init__(self, response: dict):
        self._response = response

    async def complete(self, **kwargs) -> LLMResponse:
        return LLMResponse(raw_text=json.dumps(self._response), model="stub")


@pytest.mark.asyncio
async def test_analyzer_converts_ai_errors_to_findings():
    settings = get_settings()
    provider = _StubProvider(
        {
            "errors": [
                {
                    "category": "style",
                    "severity": "warning",
                    "location": "Введение",
                    "original_text": "Я хочу рассказать...",
                    "explanation": "Разговорная формулировка.",
                    "suggestion": "В работе рассматривается...",
                    "confidence": 0.9,
                }
            ]
        }
    )
    analyzer = AIAnalyzer(provider, settings, PromptLibrary(settings.prompts_dir))
    findings, ok = await analyzer.analyze({"introduction": "Я хочу рассказать про важную тему."})
    assert ok is True
    assert any(f.source.value == "ai" for f in findings)
