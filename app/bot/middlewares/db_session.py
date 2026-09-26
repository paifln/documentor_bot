from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.types import User as TgUser

from app.config.settings import get_settings
from app.database.repositories.user_repository import UserRepository
from app.database.session import async_session_factory


class DbSessionMiddleware(BaseMiddleware):
    """Opens one AsyncSession per update and makes the current app User row
    available to handlers via data['db_user'].

    Commits happen at two points: right after resolving/creating the user
    (so the user row is durable even if the handler itself fails later),
    and again after the handler returns successfully. The second commit is
    a safety net — most handlers that write also commit explicitly, but a
    handler that forgets to would otherwise have its changes silently
    discarded when the session closes at the end of this context manager
    (AsyncSession does NOT auto-commit on a clean exit, only on explicit
    commit()).
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        settings = get_settings()

        async with async_session_factory() as session:
            data["session"] = session
            if tg_user is not None:
                repo = UserRepository(session)
                db_user = await repo.get_or_create(
                    telegram_id=tg_user.id,
                    username=tg_user.username,
                    full_name=tg_user.full_name,
                    admin_ids=settings.admin_id_list,
                )
                data["db_user"] = db_user
                data["user_language"] = db_user.language or "ru"
                await session.commit()

            try:
                result = await handler(event, data)
            except Exception:
                await session.rollback()
                raise
            await session.commit()
            return result
