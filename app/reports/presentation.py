"""Shared presentation policy for Telegram and PDF, including historical results."""

from app.common.models import CategoryScore, CheckResult
from app.i18n import t


def score_over_100(result: CheckResult) -> float:
    return round(result.score / result.max_score * 100, 1) if result.max_score else 0.0


def score_note(result: CheckResult, lang: str) -> str:
    if result.provisional or not result.ai_analysis_available:
        reasons = " ".join(
            t(f"ai.reason.{reason}", lang)
            for reason in dict.fromkeys(result.ai_failure_reasons)
            if reason
            in {"budget", "timeout", "provider", "invalid_response", "disabled", "empty_text"}
        )
        return (t("score.provisional", lang) + " " + reasons).strip()
    return t("score.complete", lang)


def category_value(category: CategoryScore, lang: str) -> str:
    if not category.evaluated:
        return t("not_evaluated", lang)
    value = f"{category.earned_points:g}/{category.max_points:g}"
    if category.coverage < 1:
        value += " · " + t("score.coverage", lang, pct=round(category.coverage * 100))
    return value
