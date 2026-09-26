import asyncio
import datetime as dt
import os
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.common.enums import CheckStatus, UserRole
from app.common.exceptions import DailyLimitExceededError
from app.common.models import CheckResult, CheckSummary, Finding
from app.config.settings import Settings
from app.database.models import Check, FindingRecord
from app.database.repositories.check_repository import CheckRepository
from app.database.repositories.user_repository import UserRepository
from app.database.session import Base
from app.services.checks import restore_result, submit_check


@pytest.fixture
async def sessions(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def user(session, telegram_id):
    row = await UserRepository(session).get_or_create(telegram_id, None, None, [])
    await session.commit()
    return row


async def submitted(sessions, preset, tmp_path):
    async with sessions() as session:
        owner = await user(session, 101)
        path = tmp_path / "input.docx"
        path.write_bytes(b"source")
        check = await submit_check(
            session,
            owner.id,
            owner.telegram_id,
            "input.docx",
            6,
            preset,
            {
                "docx_path": str(path),
                "chat_id": 101,
                "progress_message_id": 1,
                "lang": "en",
                "display_filename": "input.docx",
            },
            Settings(_env_file=None),
        )
        return check.id, path


@pytest.mark.asyncio
async def test_owner_isolation_and_snapshot(sessions, sample_preset, tmp_path):
    check_id, _ = await submitted(sessions, sample_preset, tmp_path)
    async with sessions() as session:
        repo = CheckRepository(session)
        assert await repo.get_for_user(check_id, 202) is None
        check = await repo.get_for_user(check_id, 101)
        assert check.status == CheckStatus.PENDING
        result = CheckResult(
            score=0,
            summary=CheckSummary(),
            findings=[
                Finding(
                    category="content",
                    severity="warning",
                    source="ai",
                    message="issue",
                    original_text="quoted",
                )
            ],
        )
        await repo.complete(check, result)
        await repo.complete(check, result)
        await session.commit()
        assert await session.scalar(select(func.count(FindingRecord.id))) == 1
        sample_preset.scoring.content = 99
        restored = restore_result(check)
        assert restored.score == 0
        assert restored.findings[0].original_text == "quoted"
        await repo.fail(check, "delivery failed")
        assert check.status == CheckStatus.COMPLETED


@pytest.mark.asyncio
async def test_concurrent_quota(sessions, sample_preset):
    async with sessions() as session:
        owner = await user(session, 101)
    settings = Settings(_env_file=None, MAX_ACTIVE_CHECKS=1)

    async def submit():
        async with sessions() as session:
            try:
                await submit_check(session, owner.id, 101, "a.docx", 1, sample_preset, {}, settings)
                return True
            except DailyLimitExceededError:
                await session.rollback()
                return False

    assert sorted(await asyncio.gather(submit(), submit())) == [False, True]


@pytest.mark.asyncio
async def test_admin_role_is_revoked(sessions):
    async with sessions() as session:
        repo = UserRepository(session)
        row = await repo.get_or_create(101, None, None, [101])
        await session.commit()
        assert row.role == UserRole.ADMIN
    async with sessions() as session:
        row = await UserRepository(session).get_or_create(101, None, None, [])
        assert row.role == UserRole.USER


@pytest.mark.asyncio
async def test_outbox_recovers_and_dispatches(sessions, sample_preset, tmp_path, monkeypatch):
    from app.services import dispatch

    check_id, _ = await submitted(sessions, sample_preset, tmp_path)
    async with sessions() as session:
        check = await session.get(Check, check_id)
        check.status = CheckStatus.RUNNING
        check.started_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=2)
        await session.commit()
    queued = []

    async def enqueue(**kwargs):
        queued.append(kwargs["check_id"])

    monkeypatch.setattr(dispatch, "async_session_factory", sessions)
    monkeypatch.setattr(dispatch, "enqueue_check_job", enqueue)
    await dispatch.dispatch_pending()
    assert queued == [check_id]
    async with sessions() as session:
        assert (await session.get(Check, check_id)).status == CheckStatus.PENDING


@pytest.mark.asyncio
async def test_cancelled_worker_preserves_source(sessions, sample_preset, tmp_path, monkeypatch):
    from app import worker

    check_id, path = await submitted(sessions, sample_preset, tmp_path)

    async def close():
        pass

    async def run(*args, **kwargs):
        raise asyncio.CancelledError()

    fake = SimpleNamespace(session=SimpleNamespace(close=close))
    pipeline = SimpleNamespace(
        run=run, ai_analyzer=SimpleNamespace(provider=SimpleNamespace(aclose=close))
    )
    monkeypatch.setattr(worker, "Bot", lambda **kwargs: fake)
    monkeypatch.setattr(worker, "build_pipeline", lambda settings: pipeline)
    monkeypatch.setattr(worker, "async_session_factory", sessions)
    with pytest.raises(asyncio.CancelledError):
        await worker.run_check_job({}, check_id=check_id)
    assert path.exists()
    async with sessions() as session:
        assert (await session.get(Check, check_id)).status == CheckStatus.PENDING


@pytest.mark.asyncio
async def test_delivery_failure_keeps_completed_result(
    sessions, sample_preset, tmp_path, monkeypatch
):
    from app import worker

    check_id, _ = await submitted(sessions, sample_preset, tmp_path)
    result = CheckResult(score=42, summary=CheckSummary())
    async with sessions() as session:
        check = await session.get(Check, check_id)
        await CheckRepository(session).complete(check, result)
        payload = check.job_payload
        await session.commit()

    def failing_pdf(*args):
        raise OSError("disk full")

    monkeypatch.setattr(worker, "async_session_factory", sessions)
    monkeypatch.setattr(worker, "generate_pdf", failing_pdf)
    from unittest.mock import AsyncMock

    bot = SimpleNamespace(edit_message_text=AsyncMock())
    await worker.deliver_result(bot, check_id, result, sample_preset, payload)
    async with sessions() as session:
        check = await session.get(Check, check_id)
        assert check.status == CheckStatus.COMPLETED
        assert check.score == 42
        assert check.delivery_status == "pending"
    bot.edit_message_text.assert_not_awaited()
    for _ in range(worker.get_settings().max_job_attempts - 1):
        await worker.deliver_result(bot, check_id, result, sample_preset, payload)
    bot.edit_message_text.assert_awaited_once()
    assert bot.edit_message_text.call_args.kwargs["text"] == worker.t(
        "delivery.failed", payload["lang"]
    )
    async with sessions() as session:
        check = await session.get(Check, check_id)
        assert check.delivery_status == "failed"
        assert check.result_snapshot["score"] == 42


@pytest.mark.asyncio
async def test_delivery_success_clears_progress(sessions, sample_preset, tmp_path, monkeypatch):
    from unittest.mock import AsyncMock

    from app import worker

    check_id, _ = await submitted(sessions, sample_preset, tmp_path)
    result = CheckResult(score=42, summary=CheckSummary())
    async with sessions() as session:
        check = await session.get(Check, check_id)
        await CheckRepository(session).complete(check, result)
        payload = check.job_payload
        await session.commit()
    bot = SimpleNamespace(
        edit_message_text=AsyncMock(), send_message=AsyncMock(), send_document=AsyncMock()
    )
    monkeypatch.setattr(worker, "async_session_factory", sessions)
    monkeypatch.setattr(worker, "generate_pdf", lambda *args: tmp_path / "report.pdf")
    await worker.deliver_result(bot, check_id, result, sample_preset, payload)
    bot.send_document.assert_awaited_once()
    bot.edit_message_text.assert_awaited_once()
    assert bot.edit_message_text.call_args.kwargs["text"] == worker.t(
        "delivery.sent", payload["lang"]
    )
    async with sessions() as session:
        assert (await session.get(Check, check_id)).delivery_status == "sent"


@pytest.mark.skipif(os.environ.get("RUN_SERVICE_TESTS") != "1", reason="Requires isolated Redis")
@pytest.mark.asyncio
async def test_real_queue_runs_worker_and_replay_uses_snapshot(
    sessions, sample_preset, tmp_path, monkeypatch, correct_docx
):
    from arq.connections import RedisSettings, create_pool
    from arq.worker import Worker

    from app import worker
    from app.config.settings import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "storage_dir", tmp_path)
    monkeypatch.setattr(settings, "reports_dir", tmp_path / "reports")
    monkeypatch.setattr(settings, "llm_provider", "mock")
    settings.reports_dir.mkdir()
    check_id, path = await submitted(sessions, sample_preset, tmp_path)
    path.write_bytes(correct_docx.read_bytes())
    sent = []

    async def close():
        pass

    async def send(**kwargs):
        sent.append(kwargs)

    fake = SimpleNamespace(
        session=SimpleNamespace(close=close),
        send_message=send,
        send_document=send,
        edit_message_text=send,
    )
    monkeypatch.setattr(worker, "Bot", lambda **kwargs: fake)
    monkeypatch.setattr(worker, "async_session_factory", sessions)
    queue = f"test-worker:{uuid.uuid4()}"
    job_id = f"test:{uuid.uuid4()}"
    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    runner = Worker(
        [worker.run_check_job],
        redis_pool=pool,
        queue_name=queue,
        burst=True,
        handle_signals=False,
        keep_result=0,
    )
    try:
        await pool.enqueue_job(
            "run_check_job", check_id=check_id, _queue_name=queue, _job_id=job_id
        )
        await runner.async_run()
        assert runner.jobs_complete == 1
        async with sessions() as session:
            check = await session.get(Check, check_id)
            assert check.status == CheckStatus.COMPLETED
            assert check.delivery_status == "sent"
            assert check.result_snapshot["ai_analysis_available"] is False
            assert check.result_snapshot["max_score"] == 50
        assert not path.exists()
        assert (settings.reports_dir / f"report_{check_id}.pdf").exists()
        count = len(sent)
        await worker.run_check_job({}, check_id=check_id)
        assert len(sent) == count
    finally:
        await pool.delete(queue, f"arq:job:{job_id}", f"{queue}:health-check")
        # arq 0.26 close(handle_signals=False) references Unix SIGUSR1 on Windows.
        # Burst mode has finished all tasks; this test owns and closes its pool.
        await pool.aclose()


@pytest.mark.asyncio
async def test_delete_history_is_scoped_to_user(sessions, sample_preset, tmp_path, monkeypatch):
    from app.services import retention

    check_id, _ = await submitted(sessions, sample_preset, tmp_path)
    async with sessions() as session:
        check = await session.get(Check, check_id)
        await CheckRepository(session).complete(check, CheckResult(score=0, summary=CheckSummary()))
        await session.commit()
    monkeypatch.setattr(retention, "async_session_factory", sessions)
    assert await retention.delete_user_history(202) == 0
    assert await retention.delete_user_history(101) == 1
    async with sessions() as session:
        assert await session.get(Check, check_id) is None
