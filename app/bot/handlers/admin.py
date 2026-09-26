from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import CheckStatus, UserRole
from app.database.models.check import Check
from app.database.models.user import User
from app.i18n import t
from app.rules.presets.loader import get_preset_registry

router = Router(name="admin")


def _require_admin(db_user: User) -> bool:
    return db_user.role == UserRole.ADMIN


@router.message(Command("admin"))
async def admin_root(message: Message, db_user: User) -> None:
    if not _require_admin(db_user):
        await message.answer(t("admin.only", db_user.language or "ru"))
        return

    text = (
        "🛠 Панель администратора\n\n"
        "/admin_stats — статистика по проверкам\n"
        "/admin_presets — список активных наборов требований\n\n"
        "Для добавления нового набора требований создайте .yaml файл в "
        "директории rules/presets/ и перезапустите приложение — изменения "
        "в коде Python не требуются."
    )
    await message.answer(text)


@router.message(Command("admin_stats"))
async def admin_stats(message: Message, db_user: User, session: AsyncSession) -> None:
    if not _require_admin(db_user):
        await message.answer(t("admin.only", db_user.language or "ru"))
        return

    total_checks = (
        await session.execute(
            select(func.count(Check.id)).where(Check.status == CheckStatus.COMPLETED)
        )
    ).scalar_one()
    avg_score = (
        await session.execute(
            select(func.avg(Check.score)).where(
                Check.status == CheckStatus.COMPLETED, Check.ai_analysis_available.is_(True)
            )
        )
    ).scalar_one()
    total_users = (await session.execute(select(func.count(User.id)))).scalar_one()

    text = (
        "📊 Статистика системы:\n\n"
        f"Пользователей: {total_users}\n"
        f"Проверок выполнено: {total_checks}\n"
        f"Средний балл полных проверок: {round(avg_score, 1) if avg_score is not None else '—'}"
    )
    await message.answer(text)


@router.message(Command("admin_presets"))
async def admin_presets(message: Message, db_user: User) -> None:
    if not _require_admin(db_user):
        await message.answer(t("admin.only", db_user.language or "ru"))
        return

    registry = get_preset_registry()
    presets = registry.list_active()
    if not presets:
        await message.answer("Активных наборов требований не найдено.")
        return

    lines = ["📚 Активные наборы требований:\n"]
    for p in presets:
        lines.append(f"• {p.id} — {p.name} ({p.work_type.value})")
    await message.answer("\n".join(lines))
