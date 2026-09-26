"""Durable job payloads, immutable results and independent delivery state."""

import sqlalchemy as sa
from alembic import op

revision = "0003_durable_checks"
down_revision = "0002_add_user_language"
branch_labels = None
depends_on = None


def upgrade():
    for name in ("result_snapshot", "preset_snapshot", "job_payload"):
        op.add_column("checks", sa.Column(name, sa.JSON(), nullable=True))
    for name in ("attempts", "delivery_attempts"):
        op.add_column("checks", sa.Column(name, sa.Integer(), nullable=False, server_default="0"))
    op.add_column(
        "checks",
        sa.Column("delivery_status", sa.String(24), nullable=False, server_default="pending"),
    )
    op.add_column("checks", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    # Pre-migration jobs have no durable payload and cannot be resumed safely.
    op.execute(
        "UPDATE checks SET status='failed', error_detail='Legacy task requires resubmission' WHERE status IN ('pending', 'running')"
    )


def downgrade():
    with op.batch_alter_table("checks") as batch:
        for name in (
            "result_snapshot",
            "preset_snapshot",
            "job_payload",
            "attempts",
            "delivery_attempts",
            "delivery_status",
            "started_at",
        ):
            batch.drop_column(name)
