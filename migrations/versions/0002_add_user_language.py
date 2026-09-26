"""add users.language

Revision ID: 0002_add_user_language
Revises: 0001_initial
Create Date: 2026-09-11

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_user_language"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("language", sa.String(length=8), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "language")
