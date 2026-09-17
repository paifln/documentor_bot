from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.database.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def set_language(self, user: User, language: str) -> None:
        user.language = language
        await self.session.flush()

    async def get_or_create(
        self, telegram_id: int, username: str | None, full_name: str | None, admin_ids: list[int]
    ) -> User:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            return user
        role = UserRole.ADMIN if telegram_id in admin_ids else UserRole.USER
        user = User(telegram_id=telegram_id, username=username, full_name=full_name, role=role)
        self.session.add(user)
        await self.session.flush()
        return user
