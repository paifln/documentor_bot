from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.states import CB
from app.database.models.user import User
from app.database.repositories.check_repository import CheckRepository
from app.i18n import t
from app.services.retention import delete_user_history

router = Router(name="settings")


@router.callback_query(F.data == CB.HISTORY)
async def show_history(callback: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    lang = db_user.language or "ru"
    check_repo = CheckRepository(session)
    checks = await check_repo.history_for_user(db_user.telegram_id, limit=10)

    if not checks:
        await callback.message.answer(t("history.empty", lang))
        await callback.answer()
        return

    lines = [t("history.title", lang)]
    for c in checks:
        date_str = c.created_at.strftime("%d.%m.%Y")
        filename = c.document.filename if c.document else "—"
        maximum = (c.result_snapshot or {}).get("max_score", 100)
        score_str = f"{c.score:.0f}/{maximum:.0f}" if c.score is not None else c.status.value
        lines.append(f"{date_str}\n{filename}\n{score_str}\n")

    await callback.message.answer("\n".join(lines))
    await callback.answer()


@router.callback_query(F.data == CB.SETTINGS)
async def show_settings(callback: CallbackQuery, db_user: User) -> None:
    await callback.message.answer(t("settings.text", db_user.language or "ru"))
    await callback.answer()


@router.message(Command("delete_my_data"))
async def delete_history(message: Message, db_user: User):
    count = await delete_user_history(db_user.telegram_id)
    await message.answer(t("history.deleted", db_user.language or "ru", n=count))
