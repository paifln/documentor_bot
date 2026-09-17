from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.states import CB
from app.database.models.user import User
from app.database.repositories.check_repository import CheckRepository
from app.i18n import t

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
        score_str = f"{c.score:.0f}/100" if c.score is not None else c.status.value
        lines.append(f"{date_str}\n{filename}\n{score_str}\n")

    await callback.message.answer("\n".join(lines))
    await callback.answer()


@router.callback_query(F.data == CB.SETTINGS)
async def show_settings(callback: CallbackQuery, db_user: User) -> None:
    await callback.message.answer(t("settings.text", db_user.language or "ru"))
    await callback.answer()
