"""Add full_name and organization to users table

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-07 00:00:00.000000

Uses IF NOT EXISTS so this migration is idempotent on DBs created via create_all.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # IF NOT EXISTS makes this safe for DBs already created via create_all
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255)"
    )
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS organization VARCHAR(255)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS full_name")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS organization")
