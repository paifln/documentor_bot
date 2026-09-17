"""LLMProvider abstraction (spec §3/§12).

The rest of the system only ever talks to this interface, never to a
vendor SDK directly. Adding a new vendor = implementing one class here.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass

from tenacity import retry, stop_after_attempt, wait_exponential

from app.common.exceptions import AIProviderError, AIQuotaExceededError
from app.config.logging import get_logger
from app.config.settings import Settings

logger = get_logger(__name__)


@dataclass
class LLMResponse:
    raw_text: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMProvider(ABC):
    """Abstract chat-completion provider that always returns raw text,
    which callers then validate against a Pydantic schema (spec §13)."""

    name: str = "abstract"

    @abstractmethod
    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.2,
    ) -> LLMResponse: ...

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
    ) -> dict:
        """Call the model and parse strict JSON out of the response,
        stripping markdown code fences if the model added them anyway."""
        response = await self.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            temperature=0.1,
        )
        text = response.raw_text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            logger.warning("ai_json_parse_failed", provider=self.name)
            raise AIProviderError(f"model returned invalid JSON: {exc}") from exc


class OpenAIProvider(LLMProvider):
    """Talks to OpenAI-compatible chat completion APIs."""

    name = "openai"

    def __init__(self, settings: Settings):
        from openai import AsyncOpenAI  # local import: keep optional dependency lazy

        self._client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url or None,
            timeout=settings.llm_timeout_seconds,
        )
        self._model = settings.llm_model
        self._max_retries = settings.llm_max_retries

    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.2,
    ) -> LLMResponse:
        @retry(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            reraise=True,
        )
        async def _call():
            return await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"},
            )

        try:
            completion = await _call()
        except Exception as exc:  # noqa: BLE001
            message = str(exc).lower()
            if "rate limit" in message or "quota" in message:
                raise AIQuotaExceededError(str(exc)) from exc
            raise AIProviderError(str(exc)) from exc

        choice = completion.choices[0]
        usage = completion.usage
        return LLMResponse(
            raw_text=choice.message.content or "",
            model=self._model,
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
        )


class AnthropicProvider(LLMProvider):
    """Placeholder for future Claude integration (spec §3: 'В будущем').

    Left unimplemented intentionally — wiring in the Anthropic SDK is a
    small, isolated change once credentials/model choice are decided.
    """

    name = "anthropic"

    def __init__(self, settings: Settings):
        raise NotImplementedError(
            "AnthropicProvider is a placeholder. Implement using the "
            "anthropic Python SDK following the same interface as OpenAIProvider."
        )

    async def complete(self, **kwargs) -> LLMResponse:  # pragma: no cover
        raise NotImplementedError


class GoogleProvider(LLMProvider):
    """Placeholder for future Gemini integration."""

    name = "google"

    def __init__(self, settings: Settings):
        raise NotImplementedError("GoogleProvider is a placeholder for future work.")

    async def complete(self, **kwargs) -> LLMResponse:  # pragma: no cover
        raise NotImplementedError


class LocalLLMProvider(LLMProvider):
    """Placeholder for a self-hosted model server (e.g. vLLM/Ollama)."""

    name = "local"

    def __init__(self, settings: Settings):
        raise NotImplementedError("LocalLLMProvider is a placeholder for future work.")

    async def complete(self, **kwargs) -> LLMResponse:  # pragma: no cover
        raise NotImplementedError


class MockProvider(LLMProvider):
    """Deterministic offline provider used in tests and local dev without
    an API key (spec §31: 'использовать mock, чтобы тесты не зависели от API')."""

    name = "mock"

    def __init__(self, settings: Settings | None = None):
        pass

    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.2,
    ) -> LLMResponse:
        return LLMResponse(raw_text=json.dumps({"errors": []}), model="mock")


def build_llm_provider(settings: Settings) -> LLMProvider:
    providers: dict[str, type[LLMProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "google": GoogleProvider,
        "local": LocalLLMProvider,
        "mock": MockProvider,
    }
    provider_cls = providers.get(settings.llm_provider.lower())
    if provider_cls is None:
        logger.warning("unknown_llm_provider_falling_back_to_mock", provider=settings.llm_provider)
        provider_cls = MockProvider
    return provider_cls(settings)
