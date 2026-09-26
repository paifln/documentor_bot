import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from app.api.app import app
from app.api.dependencies import db_session
from app.config.settings import get_settings
from app.database.repositories.check_repository import CheckRepository


@pytest.mark.asyncio
async def test_api_requires_token_and_checks_owner(monkeypatch):
    token = "test-token-" + "a" * 32
    monkeypatch.setattr(get_settings(), "api_tokens", {token: 101})

    async def session():
        yield object()

    calls = []

    async def get_for_user(self, check_id, telegram_id):
        calls.append((check_id, telegram_id))
        return None

    monkeypatch.setattr(CheckRepository, "get_for_user", get_for_user)
    app.dependency_overrides[db_session] = session
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (await client.get("/api/v1/checks/1")).status_code == 401
            assert not calls
            assert (
                await client.get("/api/v1/checks/1", headers={"Authorization": f"Bearer {token}"})
            ).status_code == 404
            assert calls == [(1, 101)]
    finally:
        app.dependency_overrides.clear()


def test_migrations_upgrade_existing_sqlite(tmp_path):
    database = tmp_path / "migration.db"
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite+aiosqlite:///{database}",
        "STORAGE_DIR": str(tmp_path / "storage"),
        "REPORTS_DIR": str(tmp_path / "reports"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    root = Path(__file__).resolve().parents[1]
    command = [sys.executable, "-m", "alembic"]
    for target in ("0002_add_user_language", "head"):
        result = subprocess.run(
            command + ["upgrade", target], cwd=root, env=env, capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr
    with sqlite3.connect(database) as connection:
        columns = {r[1] for r in connection.execute("PRAGMA table_info(checks)")}
        assert {"result_snapshot", "job_payload", "delivery_status", "preset_snapshot"} <= columns


def test_docker_context_excludes_secrets():
    root = Path(__file__).resolve().parents[1]
    dockerfile = (root / "Dockerfile").read_text()
    assert "COPY . ." not in dockerfile
    ignored = (root / ".dockerignore").read_text().splitlines()
    assert ".env" in ignored and "data" in ignored and ".git" in ignored


def test_bootstrap_adopts_legacy_schema_without_losing_users(tmp_path):
    database = tmp_path / "legacy.db"
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite+aiosqlite:///{database}",
        "STORAGE_DIR": str(tmp_path / "storage"),
        "REPORTS_DIR": str(tmp_path / "reports"),
    }
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "0002_add_user_language"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    with sqlite3.connect(database) as connection:
        connection.execute("DROP TABLE alembic_version")
        connection.execute("INSERT INTO users (telegram_id,role,language) VALUES (101,'user','ru')")
    result = subprocess.run(
        [sys.executable, "-m", "app.database.bootstrap"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT telegram_id FROM users").fetchone() == (101,)
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (
            "0003_durable_checks",
        )
