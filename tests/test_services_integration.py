"""Opt-in real PostgreSQL + Redis transport test (enabled in CI).

Uses a transaction that is rolled back and a uniquely named Redis queue.
Does not contact Telegram or an LLM.
"""

import os
import uuid

import pytest
from arq.connections import RedisSettings, create_pool
from arq.jobs import Job
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.common.models import CheckResult, CheckSummary
from app.config.settings import Settings
from app.database.repositories.check_repository import CheckRepository
from app.database.repositories.document_repository import DocumentRepository
from app.database.repositories.user_repository import UserRepository


@pytest.mark.skipif(
    os.environ.get("RUN_SERVICE_TESTS") != "1", reason="Requires isolated PostgreSQL and Redis"
)
@pytest.mark.asyncio
async def test_postgres_result_and_redis_transport():
    settings = Settings()
    engine = create_async_engine(settings.database_url)
    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    job_id = f"test:{uuid.uuid4()}"
    queue = f"test-queue:{uuid.uuid4()}"
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            user = await UserRepository(session).get_or_create(999_999_123, None, None, [])
            document = await DocumentRepository(session).create(user.id, "test.docx", 10)
            repo = CheckRepository(session)
            check = await repo.create(document.id, "test")
            await repo.complete(check, CheckResult(score=0, summary=CheckSummary()))
            assert (await repo.get_for_user(check.id, user.telegram_id)).result_snapshot[
                "score"
            ] == 0
            assert await repo.get_for_user(check.id, 999_999_124) is None
            await pool.enqueue_job(
                "run_check_job", check_id=check.id, _job_id=job_id, _queue_name=queue
            )
            info = await Job(job_id, pool, _queue_name=queue).info()
            assert info.kwargs == {"check_id": check.id}
            assert (
                await pool.enqueue_job(
                    "run_check_job", check_id=check.id, _job_id=job_id, _queue_name=queue
                )
                is None
            )
            await session.rollback()
    finally:
        await pool.delete(f"arq:job:{job_id}", queue)
        await pool.aclose()
        await engine.dispose()
