from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.database.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User)
            .where(User.telegram_id == telegram_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def set_language(self, user: User, language: str) -> None:
        user.language = language
        await self.session.flush()

    async def get_or_create(
        self, telegram_id: int, username: str | None, full_name: str | None, admin_ids: list[int]
    ) -> User:
        # Upsert avoids the concurrent first-update unique-key race on both backends.
        if self.session.bind.dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import insert
        else:
            from sqlalchemy.dialects.sqlite import insert
        role = UserRole.ADMIN if telegram_id in admin_ids else UserRole.USER
        stmt = insert(User).values(
            telegram_id=telegram_id, username=username, full_name=full_name, role=role
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[User.telegram_id],
            set_={
                "username": username,
                "full_name": full_name,
                "role": role,
            },
        )
        await self.session.execute(stmt)
        return await self.get_by_telegram_id(telegram_id)
