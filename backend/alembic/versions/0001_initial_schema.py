"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-12 21:52:58.309359

Mirrors /schema.sql at the repo root exactly (see that file's header comment and
README.md's Data model / Decisions log for full rationale). Written as the Phase 1
target — NOT applied during Phase 0, which is deliberately DB-free (see CLAUDE.md).
This migration has not been run against a real database; verify it end-to-end
before relying on it in Phase 1.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CREATE_STATEMENTS = [
    """
    CREATE TABLE sessions (
        id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        criteria_selection  JSONB NOT NULL,
        assignment_prompt   TEXT NOT NULL,
        class_name          TEXT NOT NULL,
        created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE essays (
        id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        session_id          UUID NOT NULL REFERENCES sessions(id),
        student_name        TEXT,
        essay_text          TEXT NOT NULL,
        segmentation_notes  TEXT,
        created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE essay_sentences (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        essay_id        UUID NOT NULL REFERENCES essays(id),
        sentence_index  INT NOT NULL,
        section         TEXT NOT NULL,
        span_start      INT NOT NULL,
        span_end        INT NOT NULL,
        text            TEXT NOT NULL,
        UNIQUE (essay_id, sentence_index)
    )
    """,
    """
    CREATE TABLE dispute_messages (
        id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        essay_id     UUID NOT NULL REFERENCES essays(id),
        criterion_id TEXT NOT NULL,
        role         TEXT NOT NULL,
        content      TEXT NOT NULL,
        created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE raw_grades (
        id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        essay_id            UUID NOT NULL REFERENCES essays(id),
        criterion_id        TEXT NOT NULL,
        score               SMALLINT,
        missing             BOOLEAN NOT NULL,
        strengths           JSONB NOT NULL DEFAULT '[]',
        critiques           JSONB NOT NULL DEFAULT '[]',
        reasoning           TEXT NOT NULL,
        sentence_refs        JSONB NOT NULL DEFAULT '[]',
        confidence_level     TEXT,
        confidence_reason    TEXT,
        source               TEXT NOT NULL,
        dispute_message_id   UUID REFERENCES dispute_messages(id),
        model_version         TEXT NOT NULL,
        created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE accepted_grades (
        id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        essay_id      UUID NOT NULL REFERENCES essays(id),
        criterion_id  TEXT NOT NULL,
        score         SMALLINT,
        missing       BOOLEAN NOT NULL,
        raw_grade_id  UUID NOT NULL REFERENCES raw_grades(id),
        accepted_via  TEXT NOT NULL,
        created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX idx_essay_sentences_lookup     ON essay_sentences(essay_id, sentence_index)",
    "CREATE INDEX idx_raw_grades_essay_criterion ON raw_grades(essay_id, criterion_id)",
    "CREATE INDEX idx_accepted_grades_lookup     ON accepted_grades(essay_id, criterion_id, created_at DESC)",
    "CREATE INDEX idx_dispute_messages_thread    ON dispute_messages(essay_id, criterion_id, created_at)",
]

# Reverse dependency order for teardown: accepted_grades and raw_grades reference
# dispute_messages/essays; essay_sentences/dispute_messages/essays reference
# sessions transitively via essays; sessions has no dependents.
_DROP_TABLES_IN_ORDER = [
    "accepted_grades",
    "raw_grades",
    "dispute_messages",
    "essay_sentences",
    "essays",
    "sessions",
]


def upgrade() -> None:
    for statement in _CREATE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for table_name in _DROP_TABLES_IN_ORDER:
        op.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
