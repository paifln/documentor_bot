from __future__ import annotations

import secrets
from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.database.session import get_session

_bearer = HTTPBearer(auto_error=False)


async def authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> int:
    if credentials is not None:
        for token, user_id in get_settings().api_tokens.items():
            if secrets.compare_digest(credentials.credentials, token):
                return user_id
    raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})


async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session
