"""The end-to-end analysis pipeline (spec §1, §28).

    DOCX
     ↓
    security validation
     ↓
    parse (app.document.parser)
     ↓
    RULE ENGINE (local, deterministic)
     ↓
    AI ANALYSIS (only the text, chunked)
     ↓
    AGGREGATION + SCORING
     ↓
    CheckResult

Each stage is awaited so the Telegram handler can emit progress messages
between them (spec §2 stage messages).
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from app.ai.analyzer import AIAnalyzer, PromptLibrary
from app.ai.provider import build_llm_provider
from app.ai.result import AIAnalysisResult
from app.analysis.aggregator import aggregate
from app.common.exceptions import TooManyPagesError
from app.common.models import CheckResult
from app.config.logging import get_logger
from app.config.settings import Settings
from app.document import structure as structure_module
from app.document.parser import ParsedDocument, parse_docx
from app.rules.engine import RuleEngine
from app.rules.models import RulePreset
from app.security.validation import run_all_validations

logger = get_logger(__name__)


def build_pipeline(settings: Settings) -> "AnalysisPipeline":
    """Factory used by both the worker process and tests to construct a
    fully-wired pipeline from application settings."""
    provider = build_llm_provider(settings)
    analyzer = AIAnalyzer(provider, settings, PromptLibrary(settings.prompts_dir))
    return AnalysisPipeline(RuleEngine(), analyzer)


ProgressCallback = Callable[[str], Awaitable[None]]


async def _noop_progress(_: str) -> None:
    return None


class AnalysisPipeline:
    def __init__(self, rule_engine: RuleEngine, ai_analyzer: AIAnalyzer):
        self.rule_engine = rule_engine
        self.ai_analyzer = ai_analyzer

    async def run(
        self,
        docx_path: Path,
        preset: RulePreset,
        topic: str = "",
        lang: str = "ru",
        on_progress: ProgressCallback | None = None,
    ) -> CheckResult:
        progress = on_progress or _noop_progress
        started = time.monotonic()

        await progress("structure")
        await asyncio.to_thread(run_all_validations, docx_path, "document.docx", None)
        document: ParsedDocument = await asyncio.to_thread(parse_docx, docx_path)
        if document.estimated_page_count > self.ai_analyzer.settings.max_pages:
            raise TooManyPagesError("Document exceeds estimated page limit")
        logger.info("document_parsed", pages_estimate=document.estimated_page_count)

        await progress("formatting")
        rule_result = await asyncio.to_thread(self.rule_engine.run, document, preset, lang)
        logger.info("rules_completed", finding_count=len(rule_result.findings))

        await progress("text")
        sections_text = structure_module.split_into_logical_sections(
            document, rule_result.structure_report
        )

        await progress("ai")
        ai_result = AIAnalysisResult(failure_reasons=["provider"])
        try:
            ai_result = await self.ai_analyzer.analyze_document(
                sections_text, topic=topic, lang=lang
            )
            logger.info(
                "ai_analysis_completed",
                finding_count=len(ai_result.findings),
                ok=ai_result.complete,
                coverage=ai_result.category_coverage,
                failure_reasons=ai_result.failure_reasons,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("ai_analysis_failed", error_type=type(exc).__name__)

        await progress("report")
        elapsed = round(time.monotonic() - started, 2)
        result = aggregate(
            rule_findings=rule_result.findings,
            ai_findings=ai_result.findings,
            preset=preset,
            sections_found=rule_result.sections_found,
            ai_available=ai_result.complete,
            ai_category_coverage=ai_result.category_coverage,
            processing_time_seconds=elapsed,
        )
        logger.info("check_completed", score=result.score, elapsed_seconds=elapsed)
        result.ai_coverage = ai_result.coverage
        result.ai_tokens_used = ai_result.tokens_used
        result.ai_failure_reasons = ai_result.failure_reasons
        return result
