"""add raw_grades.run_id

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-16

Mirrors /schema.sql's raw_grades.run_id column (see that file's comment for the
full rationale). First real incremental migration applied on top of 0001 —
0001 was hand-amended in place while nothing had been applied to any database
yet; from here on, schema changes land as new migrations, not edits to 0001.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE raw_grades ADD COLUMN run_id TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE raw_grades DROP COLUMN run_id")
