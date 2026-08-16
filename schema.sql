-- AP Lit Essay Grader — schema as of 2026-08-16 dispute-persistence session.
-- Seven tables. See README.md "Data model" and "Decisions log" (2026-08-11, 2026-08-12,
-- 2026-08-16 entries) for full rationale. Phase 0's grading pipeline (POST /grade) was
-- DB-free through 2026-08-15 (S3-logged eval runs only) — this is the first migration
-- actually applied against a real (local, docker-compose) Postgres instance.

CREATE TABLE sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id          TEXT NOT NULL,     -- Cognito `sub` — the real access boundary
    criteria_selection  JSONB NOT NULL,    -- "full essay" or a subset of the 14 criterion ids
    assignment_prompt   TEXT NOT NULL,
    class_id            TEXT NOT NULL,     -- raw display string (e.g. "Period 3 — AP Lit"), same
                                            -- value as GradeRequest.class_id/frontend session.classId.
                                            -- NOT the S3 key's slugified form (storage/result_logger.py's
                                            -- slugify_class_name()) — same underlying class, different
                                            -- string. Phase 0/1: free text; Phase 2: FK to a classes table
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE essays (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID NOT NULL REFERENCES sessions(id),
    teacher_id          TEXT NOT NULL,     -- denormalized from sessions.teacher_id — avoids a join
                                            -- for the WHERE teacher_id = sub scoping every query needs
    student_name        TEXT,              -- Phase 2 will need to pseudonymize this path
    essay_text          TEXT NOT NULL,
    segmentation_notes  TEXT,               -- set when the segmentation call had to make a judgment
                                             -- call (e.g. 3 body paragraphs found, merged into 2) —
                                             -- best-effort, never blocks, but transparent when not clean-cut
    s3_key              TEXT,               -- grading-runs/... key for this run's raw model output
                                             -- (storage/result_logger.py)
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Written once per essay by the segmentation call (pipeline step 1). Source of truth
-- for span resolution: grading calls reference sentences by index, not raw offsets or
-- quoted text, so a mis-anchored quote can't silently mis-highlight the wrong sentence.
CREATE TABLE essay_sentences (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    essay_id        UUID NOT NULL REFERENCES essays(id),
    sentence_index  INT NOT NULL,        -- 0-based, in reading order
    section         TEXT NOT NULL,       -- 'thesis' | 'body_1' | 'body_2' | 'conclusion'
    span_start      INT NOT NULL,        -- char offset into essays.essay_text
    span_end        INT NOT NULL,
    text            TEXT NOT NULL,
    UNIQUE (essay_id, sentence_index)
);

-- Append-only event log. One row per model generation: 14 rows per essay from the
-- initial thesis/body_1/body_2/conclusion calls (source matches which call produced
-- it), plus one more per dispute proposal Claude makes (source='dispute-proposal').
-- Re-grill (2026-08-16): originally a dispute re-ran its entire section call (up to 6
-- new rows per resolution); revised so propose_revised_grade is scoped to the single
-- criterion under discussion — a chat is inherently about one criterion at a time. See
-- README's 2026-08-16 Decisions log entry for the full rationale.
-- `sentence_refs` replaces raw span_start/span_end — actual offsets are resolved by
-- joining sentence_refs against essay_sentences at read/response time.
CREATE TABLE raw_grades (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    essay_id            UUID NOT NULL REFERENCES essays(id),
    criterion_id        TEXT NOT NULL,
    score               SMALLINT,        -- 1-4, null if missing
    missing             BOOLEAN NOT NULL,
    strengths           JSONB NOT NULL DEFAULT '[]',
    critiques           JSONB NOT NULL DEFAULT '[]',
    reasoning           TEXT NOT NULL,
    sentence_refs       JSONB NOT NULL DEFAULT '[]',  -- array of essay_sentences.sentence_index
    confidence_level    TEXT,            -- 'high' | 'medium' | 'low' — thesis rows only, else null
    confidence_reason   TEXT,            -- e.g. 'explicit thesis stated' / 'inferred, not stated anywhere'
    source              TEXT NOT NULL,   -- 'thesis' | 'body_1' | 'body_2' | 'conclusion' | 'dispute-proposal'
    model_version       TEXT NOT NULL,   -- e.g. 'claude-sonnet-5-zeroshot', later a fine-tuned adapter version
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Append-only, but read as "latest row per (essay_id, criterion_id) wins" — never
-- updated in place. This is the operative score: what's shown to the student, what
-- feeds the essay's overall grade, and what becomes the DPO 'preferred' value.
CREATE TABLE accepted_grades (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    essay_id      UUID NOT NULL REFERENCES essays(id),
    criterion_id  TEXT NOT NULL,
    score         SMALLINT,
    missing       BOOLEAN NOT NULL,
    raw_grade_id  UUID NOT NULL REFERENCES raw_grades(id),  -- the FK the DPO pipeline depends on
    accepted_via  TEXT NOT NULL,         -- 'bulk_finish' | 'dispute_save'
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per "Disagree with this score?" click — the parent record for a thread.
-- Redesigned 2026-08-16 (was a flat dispute_messages table keyed directly on
-- essay_id+criterion_id) to give a thread its own identity and lifecycle, and so
-- dispute_messages can map back to its essay via a single indexed join instead of
-- denormalizing essay_id onto every message row.
CREATE TABLE disputes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    essay_id            UUID NOT NULL REFERENCES essays(id),
    teacher_id          TEXT NOT NULL,               -- denormalized from essays.teacher_id —
                                                       -- avoids a join for the WHERE teacher_id = sub
                                                       -- scoping every other query in the app does
    class_id            TEXT,                        -- denormalized from sessions.class_id — purely
                                                       -- organizational (e.g. "disputes this month in
                                                       -- Period 3"), not a security boundary, same as
                                                       -- the S3 key's class_slug segment
    criterion_id        TEXT NOT NULL,                -- e.g. 'bp1-evidence-1'
    status              TEXT NOT NULL DEFAULT 'open'
                          CHECK (status IN ('open', 'resolved')),
    opened_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at         TIMESTAMPTZ,
    resolution          TEXT
                          CHECK (resolution IN ('corrected', 'kept_original')),
    accepted_grade_id   UUID REFERENCES accepted_grades(id),  -- set on resolve

    CONSTRAINT one_open_dispute_per_criterion
      UNIQUE (essay_id, criterion_id, status)
      DEFERRABLE INITIALLY IMMEDIATE
);

CREATE TABLE dispute_messages (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dispute_id        UUID NOT NULL REFERENCES disputes(id),
    role              TEXT NOT NULL CHECK (role IN ('teacher', 'claude')),
    message_text      TEXT NOT NULL,
    proposed_score    INT CHECK (proposed_score BETWEEN 1 AND 4),
    raw_grade_id      UUID REFERENCES raw_grades(id),   -- source='dispute-proposal' row, set
                                                          -- whenever propose_revised_grade fired,
                                                          -- even if the proposal's score is null
                                                          -- (a "revise to missing" proposal)
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- One-directional: a proposed score always has a linked raw_grades row, but a
    -- linked row doesn't require a non-null score (missing=true proposals have
    -- score=null yet still produce a real raw_grades row to point at).
    CHECK (proposed_score IS NULL OR raw_grade_id IS NOT NULL)
);

CREATE INDEX idx_essay_sentences_lookup     ON essay_sentences(essay_id, sentence_index);
CREATE INDEX idx_raw_grades_essay_criterion ON raw_grades(essay_id, criterion_id);
CREATE INDEX idx_accepted_grades_lookup     ON accepted_grades(essay_id, criterion_id, created_at DESC);
CREATE INDEX idx_dispute_messages_dispute_id ON dispute_messages(dispute_id);
CREATE INDEX idx_disputes_essay_id           ON disputes(essay_id);
CREATE INDEX idx_disputes_teacher_id         ON disputes(teacher_id);
CREATE INDEX idx_disputes_open               ON disputes(essay_id) WHERE status = 'open';

-- An "agreement" case (SFT) = accepted_grades.score matches its raw_grades.score.
-- An "override" case (DPO) = they differ. No separate classification column needed —
-- falls out of comparing the two tables, same as originally scoped.
