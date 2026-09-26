"""Upgrade local SQLite, adopting only recognized legacy create_all schemas.

No data is removed. Unknown unversioned schemas require an explicit migration
decision instead of blindly stamping an arbitrary database as current.
"""

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.config.settings import get_settings
from app.database import models  # noqa: F401
from app.database.session import Base

_NEW_CHECK_COLUMNS = {
    "result_snapshot",
    "preset_snapshot",
    "job_payload",
    "attempts",
    "delivery_attempts",
    "delivery_status",
    "started_at",
}


def upgrade_local_database():
    settings = get_settings()
    if not settings.database_url.startswith("sqlite+aiosqlite:"):
        raise ValueError("Automatic bootstrap is only supported for local SQLite")
    engine = create_engine(settings.database_url.replace("sqlite+aiosqlite:", "sqlite:", 1))
    config = Config("alembic.ini")
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        if tables and "alembic_version" not in tables:
            expected = {
                table.name: set(table.columns.keys()) for table in Base.metadata.sorted_tables
            }
            expected["checks"] -= _NEW_CHECK_COLUMNS
            actual = {name: {c["name"] for c in inspector.get_columns(name)} for name in tables}
            revision = "0002_add_user_language"
            if "language" not in actual.get("users", set()):
                expected["users"].discard("language")
                revision = "0001_initial"
            if actual != expected:
                raise RuntimeError(
                    "Unrecognized unversioned SQLite schema; back up and migrate explicitly"
                )
            command.stamp(config, revision)
        command.upgrade(config, "head")
    finally:
        engine.dispose()


if __name__ == "__main__":
    upgrade_local_database()
