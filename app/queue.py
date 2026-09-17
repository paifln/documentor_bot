"""Thin wrapper around arq's Redis pool.

Why arq (spec §36 asks to pick one of Celery/RQ/Arq and justify it):
  * arq is asyncio-native — it fits an aiogram 3.x / FastAPI codebase far
    better than Celery (which is sync-first and needs extra bridging) or
    RQ (also sync-worker based).
  * It uses the same Redis instance already required for caching, so no
    extra infrastructure component is introduced.
  * Job functions are plain async Python functions, keeping the worker
    code consistent in style with the rest of the app.
"""

from __future__ import annotations

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config.settings import get_settings

_pool: ArqRedis | None = None


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


async def get_arq_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(_redis_settings())
    return _pool


async def enqueue_check_job(**kwargs) -> None:
    pool = await get_arq_pool()
    await pool.enqueue_job("run_check_job", **kwargs)
