"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-10

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("full_name", sa.String(length=128), nullable=True),
        sa.Column("role", sa.Enum("user", "admin", name="userrole"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"])

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("received", "validated", "parsed", "rejected", "deleted", name="documentstatus"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])

    op.create_table(
        "checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("rule_preset_id", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "completed", "failed", name="checkstatus"),
            nullable=False,
        ),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("critical_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warning_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processing_time_seconds", sa.Float(), nullable=True),
        sa.Column("ai_analysis_available", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("error_detail", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_checks_document_id", "checks", ["document_id"])

    op.create_table(
        "findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("check_id", sa.Integer(), sa.ForeignKey("checks.id"), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "formatting", "structure", "language", "style", "content",
                "references", "system", name="findingcategory",
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum("critical", "error", "warning", "info", "pass", name="severity"),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.Enum("rule_engine", "ai", name="findingsource"),
            nullable=False,
        ),
        sa.Column("rule_id", sa.String(length=128), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("expected", sa.String(length=255), nullable=True),
        sa.Column("actual", sa.String(length=255), nullable=True),
        sa.Column("suggestion", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
    )
    op.create_index("ix_findings_check_id", "findings", ["check_id"])

    op.create_table(
        "rule_presets",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("rule_presets")
    op.drop_table("findings")
    op.drop_table("checks")
    op.drop_table("documents")
    op.drop_table("users")
