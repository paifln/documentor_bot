from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.common.exceptions import CourseworkCheckerError
from app.config.logging import get_logger
from app.i18n import t

logger = get_logger(__name__)


class ErrorHandlingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except CourseworkCheckerError as exc:
            logger.error("handled_application_error", detail=exc.detail)
            await _reply_safe(event, exc.localized_message(_lang_from(data)))
        except Exception as exc:  # noqa: BLE001
            logger.error("unhandled_exception", error=str(exc), exc_info=True)
            await _reply_safe(event, t("error.internal", _lang_from(data)))


def _lang_from(data: dict[str, Any]) -> str:
    """DbSessionMiddleware runs inside this middleware and mutates the same
    `data` dict in place, so `db_user` is present here too even though this
    middleware was entered before DbSessionMiddleware ran (see main.py
    registration order) — the exception unwinds back through the same dict."""
    db_user = data.get("db_user")
    lang = getattr(db_user, "language", None) if db_user else None
    return lang or "ru"


async def _reply_safe(event: TelegramObject, text: str) -> None:
    message = getattr(event, "message", None) or event
    try:
        if hasattr(message, "answer"):
            await message.answer(text)
    except Exception:  # noqa: BLE001 - never let error reporting itself crash the bot
        pass
