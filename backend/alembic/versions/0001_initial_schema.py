"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-12 21:52:58.309359

Mirrors /schema.sql at the repo root exactly (see that file's header comment and
README.md's Data model / Decisions log for full rationale). First applied against a
real (local, docker-compose) Postgres instance 2026-08-16, alongside the dispute
persistence build — Phase 0's grading pipeline was DB-free before that.
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
        teacher_id          TEXT NOT NULL,
        criteria_selection  JSONB NOT NULL,
        assignment_prompt   TEXT NOT NULL,
        class_id            TEXT NOT NULL,
        created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE essays (
        id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        session_id          UUID NOT NULL REFERENCES sessions(id),
        teacher_id          TEXT NOT NULL,
        student_name        TEXT,
        essay_text          TEXT NOT NULL,
        segmentation_notes  TEXT,
        s3_key              TEXT,
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
    CREATE TABLE raw_grades (
        id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        essay_id            UUID NOT NULL REFERENCES essays(id),
        criterion_id        TEXT NOT NULL,
        score               SMALLINT,
        missing             BOOLEAN NOT NULL,
        strengths           JSONB NOT NULL DEFAULT '[]',
        critiques           JSONB NOT NULL DEFAULT '[]',
        reasoning           TEXT NOT NULL,
        sentence_refs       JSONB NOT NULL DEFAULT '[]',
        confidence_level    TEXT,
        confidence_reason   TEXT,
        source              TEXT NOT NULL,
        model_version       TEXT NOT NULL,
        created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
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
    """
    CREATE TABLE disputes (
        id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        essay_id            UUID NOT NULL REFERENCES essays(id),
        teacher_id          TEXT NOT NULL,
        class_id            TEXT,
        criterion_id        TEXT NOT NULL,
        status              TEXT NOT NULL DEFAULT 'open'
                              CHECK (status IN ('open', 'resolved')),
        opened_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
        resolved_at         TIMESTAMPTZ,
        resolution          TEXT
                              CHECK (resolution IN ('corrected', 'kept_original')),
        accepted_grade_id   UUID REFERENCES accepted_grades(id),

        CONSTRAINT one_open_dispute_per_criterion
          UNIQUE (essay_id, criterion_id, status)
          DEFERRABLE INITIALLY IMMEDIATE
    )
    """,
    """
    CREATE TABLE dispute_messages (
        id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        dispute_id        UUID NOT NULL REFERENCES disputes(id),
        role              TEXT NOT NULL CHECK (role IN ('teacher', 'claude')),
        message_text      TEXT NOT NULL,
        proposed_score    INT CHECK (proposed_score BETWEEN 1 AND 4),
        raw_grade_id      UUID REFERENCES raw_grades(id),
        created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

        CHECK (proposed_score IS NULL OR raw_grade_id IS NOT NULL)
    )
    """,
    "CREATE INDEX idx_essay_sentences_lookup      ON essay_sentences(essay_id, sentence_index)",
    "CREATE INDEX idx_raw_grades_essay_criterion  ON raw_grades(essay_id, criterion_id)",
    "CREATE INDEX idx_accepted_grades_lookup      ON accepted_grades(essay_id, criterion_id, created_at DESC)",
    "CREATE INDEX idx_dispute_messages_dispute_id ON dispute_messages(dispute_id)",
    "CREATE INDEX idx_disputes_essay_id           ON disputes(essay_id)",
    "CREATE INDEX idx_disputes_teacher_id         ON disputes(teacher_id)",
    "CREATE INDEX idx_disputes_open               ON disputes(essay_id) WHERE status = 'open'",
]

# Reverse dependency order for teardown.
_DROP_TABLES_IN_ORDER = [
    "dispute_messages",
    "disputes",
    "accepted_grades",
    "raw_grades",
    "essay_sentences",
    "essays",
    "sessions",
]


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    for statement in _CREATE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for table_name in _DROP_TABLES_IN_ORDER:
        op.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
