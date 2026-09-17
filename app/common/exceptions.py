"""Custom exception hierarchy.

Every exception carries an i18n `code` (see app/i18n/translations.py)
instead of a hardcoded string, so the same exception can be rendered in
whatever language the user has selected. Full technical detail (str(exc),
stack trace) must only ever go to server logs, never to the chat — see
app/bot/middlewares/error_handling.py and app/worker.py.
"""

from __future__ import annotations

from app.i18n import t


class CourseworkCheckerError(Exception):
    """Base class for all application-specific errors."""

    code: str = "error.internal"

    def __init__(self, detail: str | None = None, code: str | None = None):
        self.detail = detail or self.__class__.__name__
        if code:
            self.code = code
        super().__init__(self.detail)

    def localized_message(self, lang: str | None = None) -> str:
        return t(self.code, lang)

    @property
    def user_message(self) -> str:
        """Backward-compatible default (Russian) — prefer localized_message(lang)."""
        return self.localized_message("ru")


class FileTooLargeError(CourseworkCheckerError):
    code = "error.file_too_large"


class UnsupportedFormatError(CourseworkCheckerError):
    code = "error.unsupported_format"


class CorruptedDocumentError(CourseworkCheckerError):
    code = "error.corrupted_document"


class TextExtractionError(CourseworkCheckerError):
    code = "error.text_extraction"


class TooManyPagesError(CourseworkCheckerError):
    code = "error.too_many_pages"


class RulePresetNotFoundError(CourseworkCheckerError):
    code = "error.preset_not_found"


class AIProviderError(CourseworkCheckerError):
    code = "error.ai_provider"


class AIQuotaExceededError(CourseworkCheckerError):
    code = "error.ai_quota"


class DailyLimitExceededError(CourseworkCheckerError):
    code = "error.daily_limit"


class ReportGenerationError(CourseworkCheckerError):
    code = "error.report_generation"


class SecurityValidationError(CourseworkCheckerError):
    code = "error.security"


class InternalError(CourseworkCheckerError):
    code = "error.internal"
