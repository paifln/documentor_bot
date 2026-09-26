"""Entrypoint: starts the aiogram bot in long-polling mode.

For production, this process only handles Telegram updates and enqueues
work — see app/worker.py for the process that actually runs the analysis
pipeline (spec §36: non-blocking event loop).
"""

from __future__ import annotations

import asyncio
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.bot.handlers import admin, document, start
from app.bot.handlers import settings as settings_handlers
from app.bot.middlewares.db_session import DbSessionMiddleware
from app.bot.middlewares.error_handling import ErrorHandlingMiddleware
from app.config.logging import configure_logging, get_logger
from app.config.settings import get_settings
from app.database.session import engine
from app.queue import close_arq_pool
from app.security.files import SecureFileStore
from app.services.dispatch import dispatch_loop
from app.services.retention import purge_retained_data

logger = get_logger(__name__)


async def _purge_loop(store: SecureFileStore, interval_seconds: int = 3600) -> None:
    while True:
        try:
            await purge_retained_data()
        except Exception as exc:  # noqa: BLE001
            logger.error("purge_loop_error", error=str(exc))
        await asyncio.sleep(interval_seconds)


async def main() -> None:
    configure_logging()
    settings = get_settings()

    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")

    # Convenience for local/dev SQLite; production uses Alembic migrations.
    if settings.database_url.startswith("sqlite"):
        from app.database.bootstrap import upgrade_local_database

        await asyncio.to_thread(upgrade_local_database)

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.outer_middleware(ErrorHandlingMiddleware())
    dp.update.outer_middleware(DbSessionMiddleware())

    dp.include_router(start.router)
    dp.include_router(document.router)
    dp.include_router(settings_handlers.router)
    dp.include_router(admin.router)

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Главное меню"),
            BotCommand(command="admin", description="Панель администратора"),
        ]
    )

    store = SecureFileStore()
    purge_task = asyncio.create_task(_purge_loop(store))
    dispatch_task = asyncio.create_task(dispatch_loop())

    logger.info("bot_starting")
    try:
        await dp.start_polling(bot)
    finally:
        for task in (purge_task, dispatch_task):
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        await close_arq_pool()
        await engine.dispose()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
