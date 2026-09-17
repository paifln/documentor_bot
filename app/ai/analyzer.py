"""AI analysis orchestration (spec §12/§13/§14).

Pipeline per chunk:
  chunk text -> render prompt template -> LLMProvider.complete_json()
  -> validate against app.ai.schemas -> convert to app.common.models.Finding

Anything the model returns that fails schema validation is dropped (never
shown to the user) and logged as a warning — we never guess at malformed
AI output.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from pydantic import ValidationError

from app.ai.chunking import TextChunk, cap_chunks_to_budget, chunk_sections
from app.ai.provider import LLMProvider
from app.ai.schemas import AIErrorList, IntroductionAnalysis
from app.common.enums import FindingCategory, FindingSource, Severity
from app.common.exceptions import AIProviderError
from app.common.models import Finding
from app.config.logging import get_logger
from app.config.settings import Settings
from app.i18n import t

logger = get_logger(__name__)

_SECTION_LABEL_KEYS = {
    "introduction": "section.introduction",
    "theoretical_part": "section.theoretical_part",
    "practical_part": "section.practical_part",
    "main_body": "section.main_body",
    "conclusion": "section.conclusion",
    "references": "section.references",
    "appendix": "section.appendix",
    "abstract": "section.abstract",
}


class PromptLibrary:
    """Loads prompt templates from disk (never hardcoded in Python, spec §32)."""

    def __init__(self, prompts_dir: Path):
        self.prompts_dir = prompts_dir
        self._cache: dict[str, str] = {}

    def get(self, name: str) -> str:
        if name not in self._cache:
            path = self.prompts_dir / f"{name}.txt"
            if not path.exists():
                raise FileNotFoundError(f"prompt template not found: {path}")
            self._cache[name] = path.read_text(encoding="utf-8")
        return self._cache[name]


_CATEGORY_MAP = {
    "language": FindingCategory.LANGUAGE,
    "style": FindingCategory.STYLE,
    "content": FindingCategory.CONTENT,
    "structure": FindingCategory.STRUCTURE,
}
_SEVERITY_MAP = {
    "critical": Severity.CRITICAL,
    "error": Severity.ERROR,
    "warning": Severity.WARNING,
    "info": Severity.INFO,
}


_LANGUAGE_INSTRUCTION = {
    "ru": "Все текстовые поля ответа (explanation, suggestion, notes) пиши на русском языке.",
    "kk": "Жауаптың барлық мәтіндік өрістерін (explanation, suggestion, notes) қазақ тілінде жаз.",
    "en": "Write all text fields of the response (explanation, suggestion, notes) in English.",
}


class AIAnalyzer:
    def __init__(self, provider: LLMProvider, settings: Settings, prompts: PromptLibrary | None = None):
        self.provider = provider
        self.settings = settings
        self.prompts = prompts or PromptLibrary(settings.prompts_dir)
        self._semaphore = asyncio.Semaphore(4)  # bound concurrent LLM calls

    async def analyze(
        self, sections: dict[str, str], topic: str = "", lang: str = "ru"
    ) -> tuple[list[Finding], bool]:
        """Returns (findings, ai_fully_available).

        ai_fully_available is False if any chunk failed after retries —
        the caller must still be able to present rule-engine results and
        tell the user AI analysis was partial (spec §26 graceful degradation).
        """
        chunks = chunk_sections(sections)
        chunks = cap_chunks_to_budget(chunks, self.settings.max_ai_tokens_per_check)

        if not chunks:
            return [], True

        tasks = [self._analyze_chunk(c, topic, lang) for c in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        findings: list[Finding] = []
        ai_ok = True
        for chunk, result in zip(chunks, results):
            if isinstance(result, Exception):
                logger.warning(
                    "ai_chunk_failed",
                    section=chunk.section_key,
                    chunk_index=chunk.chunk_index,
                    error=str(result),
                )
                ai_ok = False
                continue
            findings.extend(result)

        if "introduction" in sections and sections["introduction"].strip():
            try:
                findings.extend(
                    await self._analyze_introduction(sections["introduction"], lang)
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("ai_introduction_analysis_failed", error=str(exc))
                ai_ok = False

        return findings, ai_ok

    async def _analyze_chunk(self, chunk: TextChunk, topic: str, lang: str = "ru") -> list[Finding]:
        section_label = t(_SECTION_LABEL_KEYS.get(chunk.section_key, chunk.section_key), lang)
        findings: list[Finding] = []
        language_instruction = _LANGUAGE_INSTRUCTION.get(lang, _LANGUAGE_INSTRUCTION["ru"])

        for prompt_name in ("grammar", "style", "content"):
            template = self.prompts.get(prompt_name)
            user_prompt = template.format(
                text=chunk.text,
                section_name=section_label,
                topic=topic or "не указана",
            )
            async with self._semaphore:
                try:
                    raw = await self.provider.complete_json(
                        system_prompt=(
                            "Ты — ассистент для проверки студенческих научных работ. "
                            "Всегда отвечай только валидным JSON. "
                            + language_instruction
                        ),
                        user_prompt=user_prompt,
                        max_tokens=self.settings.llm_max_output_tokens,
                    )
                except AIProviderError:
                    raise

            findings.extend(self._parse_error_list(raw, section_label))
        return findings

    async def _analyze_introduction(self, text: str, lang: str = "ru") -> list[Finding]:
        template = self.prompts.get("introduction")
        user_prompt = template.format(text=text)
        language_instruction = _LANGUAGE_INSTRUCTION.get(lang, _LANGUAGE_INSTRUCTION["ru"])
        async with self._semaphore:
            raw = await self.provider.complete_json(
                system_prompt=(
                    "Ты анализируешь структуру введения научной работы. "
                    "Отвечай только JSON. " + language_instruction
                ),
                user_prompt=user_prompt,
                max_tokens=800,
            )
        try:
            parsed = IntroductionAnalysis.model_validate(raw)
        except ValidationError as exc:
            logger.warning("ai_introduction_schema_invalid", error=str(exc))
            return []

        missing = []
        labels = {
            "has_relevance": t("label.ai.relevance", lang),
            "has_problem_statement": t("label.ai.problem", lang),
            "has_aim": t("label.ai.aim", lang),
            "has_tasks": t("label.ai.tasks", lang),
            "has_object": t("label.ai.object", lang),
            "has_subject": t("label.ai.subject", lang),
            "has_methods": t("label.ai.methods", lang),
        }
        for field, label in labels.items():
            if not getattr(parsed, field):
                missing.append(label)

        if not missing:
            return [
                Finding(
                    category=FindingCategory.CONTENT,
                    severity=Severity.PASS,
                    source=FindingSource.AI,
                    location=t("label.introduction", lang),
                    message=t("ai.introduction.complete", lang),
                    confidence=0.8,
                )
            ]

        return [
            Finding(
                category=FindingCategory.CONTENT,
                severity=Severity.WARNING,
                source=FindingSource.AI,
                location=t("label.introduction", lang),
                message=t("ai.introduction.missing", lang, elements=", ".join(missing)),
                suggestion=t("ai.introduction.missing.suggestion", lang),
                confidence=0.75,
            )
        ]

    def _parse_error_list(self, raw: dict, section_label: str) -> list[Finding]:
        try:
            parsed = AIErrorList.model_validate(raw)
        except ValidationError as exc:
            logger.warning("ai_response_schema_invalid", error=str(exc))
            return []

        findings: list[Finding] = []
        for err in parsed.errors:
            findings.append(
                Finding(
                    category=_CATEGORY_MAP.get(err.category, FindingCategory.CONTENT),
                    severity=_SEVERITY_MAP.get(err.severity, Severity.INFO),
                    source=FindingSource.AI,
                    location=err.location or section_label,
                    message=err.explanation,
                    original_text=err.original_text or None,
                    suggestion=err.suggestion or None,
                    confidence=err.confidence,
                )
            )
        return findings
