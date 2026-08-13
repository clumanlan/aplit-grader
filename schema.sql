-- AP Lit Essay Grader — schema as of 2026-08-12 backend planning session.
-- Six tables. See README.md "Data model" and "Decisions log" (2026-08-11, 2026-08-12
-- entries) for full rationale. Written as the target for a Phase 1 Alembic migration —
-- Phase 0 itself is deliberately DB-free (S3-logged eval runs only, see CLAUDE.md).

CREATE TABLE sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    criteria_selection  JSONB NOT NULL,   -- "full essay" or a subset of the 14 criterion ids
    assignment_prompt   TEXT NOT NULL,
    class_name          TEXT NOT NULL,    -- Phase 0/1: free text; Phase 2: FK to a classes table
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE essays (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID NOT NULL REFERENCES sessions(id),
    student_name        TEXT,                  -- Phase 2 will need to pseudonymize this path
    essay_text          TEXT NOT NULL,
    segmentation_notes  TEXT,                   -- set when the segmentation call had to make a
                                                 -- judgment call (e.g. 3 body paragraphs found,
                                                 -- merged into 2) — best-effort, never blocks, but
                                                 -- always transparent when it wasn't clean-cut
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

CREATE TABLE dispute_messages (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    essay_id     UUID NOT NULL REFERENCES essays(id),
    criterion_id TEXT NOT NULL,          -- e.g. 'bp1-reasoning-1', matches the UI contract's `id`
    role         TEXT NOT NULL,          -- 'teacher' | 'assistant'
    content      TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Append-only event log. One row per model generation, across all 5 pipeline calls
-- plus any dispute-triggered re-run. `source` tells you which call produced it.
-- IMPORTANT: a dispute on one criterion re-runs its ENTIRE section call (e.g. disputing
-- Evidence 1 re-runs all 6 Body ¶1 criteria, not just Evidence 1) — a correction can
-- legitimately change how sibling criteria should read, so the model isn't constrained
-- to hold them fixed. This means one dispute resolution can produce up to 6 new rows
-- here with source='dispute_proposal', but the UI only surfaces/finalizes the one
-- criterion she actually disputed — the other rows sit in the log unlinked unless she
-- separately opens a dispute on those criteria too. `accepted_grades` for the untouched
-- siblings stays pointed at whatever she accepted before; nothing auto-applies.
-- `sentence_refs` replaces raw span_start/span_end — actual offsets are resolved
-- by joining sentence_refs against essay_sentences at read/response time.
CREATE TABLE raw_grades (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    essay_id            UUID NOT NULL REFERENCES essays(id),
    criterion_id        TEXT NOT NULL,
    score               SMALLINT,        -- 1-4, null if missing
    missing             BOOLEAN NOT NULL,
    strengths           JSONB NOT NULL DEFAULT '[]',
    critiques           JSONB NOT NULL DEFAULT '[]',
    reasoning           TEXT NOT NULL,
    sentence_refs        JSONB NOT NULL DEFAULT '[]',  -- array of essay_sentences.sentence_index
    confidence_level     TEXT,           -- 'high' | 'medium' | 'low' — thesis rows only, else null
    confidence_reason    TEXT,           -- e.g. 'explicit thesis stated' / 'inferred, not stated anywhere'
    source               TEXT NOT NULL,  -- 'thesis' | 'body_1' | 'body_2' | 'conclusion' | 'dispute_proposal' | 're_grade'
    dispute_message_id   UUID REFERENCES dispute_messages(id),  -- set only when source='dispute_proposal'
    model_version         TEXT NOT NULL, -- e.g. 'claude-sonnet-5-zeroshot', later a fine-tuned adapter version
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
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

CREATE INDEX idx_essay_sentences_lookup     ON essay_sentences(essay_id, sentence_index);
CREATE INDEX idx_raw_grades_essay_criterion ON raw_grades(essay_id, criterion_id);
CREATE INDEX idx_accepted_grades_lookup     ON accepted_grades(essay_id, criterion_id, created_at DESC);
CREATE INDEX idx_dispute_messages_thread    ON dispute_messages(essay_id, criterion_id, created_at);

-- An "agreement" case (SFT) = accepted_grades.score matches its raw_grades.score.
-- An "override" case (DPO) = they differ. No separate classification column needed —
-- falls out of comparing the two tables, same as originally scoped.
