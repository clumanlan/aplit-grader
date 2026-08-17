# Frontend/Backend Integration — Gap Analysis

**Status as of 2026-08-14 (updated)**: Wiring is done. Backend embeds `label`/`group` per criterion and exposes `section_of`/`citing_criteria` (via `@computed_field`, additive — 91 backend tests still pass); CORS middleware allows the Vite dev origin; `frontend/src/api/grade.ts` is a real fetch client (`criterion_id`→`id` rename happens there, not on the backend); `GradedView.tsx` renders the sentence-centric model end-to-end (43 frontend tests pass, `tsc -b` clean). `EssayLinking.types.ts` moved to `frontend/src/types/essayLinking.ts` with one correction: `CriterionResult.group` is a display string (`"Body ¶1"`, matching `CriterionCard`/`RubricKey`'s existing rendering), not a `SectionId` — `SectionId` stays scoped to `sectionOf`/placement logic.

**Update, 2026-08-16**: the two gaps this doc's "Suggested sequencing" item 7 deferred as "bigger, separate efforts" are now both closed — see the Gap list below, updated in place rather than left to silently rot. `class_id` is now a required, consumed request field (not orphaned frontend state), and the dispute flow is a real backend round-trip, not a `setTimeout` mock. Full design/rationale for both lives in `README.md`'s 2026-08-16 Decisions log entries, not repeated here.

**Issue found during this session's smoke test, diagnosed and fixed**: driving the real pipeline against the live Claude API initially failed every time, inside the pipeline itself, at the `segmentation` or `body_1` step. Root cause for the `segmentation` failures: the model occasionally double-encodes an array-typed tool-call field as a JSON string one level too deep instead of returning it natively — verified by calling the segmentation step directly and inspecting the raw unvalidated tool output; the model's actual section binning was correct, just wrapped wrong. Fixed generically in `services/inference.py`'s `generate_structured()` (applies to all 5 pipeline calls, not just segmentation), covered by 3 new unit tests, and confirmed against the live API by replaying the exact essay that previously failed 3 times — it now succeeds. The second failure (model returned `missing: true` with a non-null `score` at `body_1`) was also root-caused and fixed: none of the system prompts or tool schemas ever told the model what `missing` should mean versus a floor score — added `MISSING_FIELD_GUIDANCE` (`services/rubric.py`) to all three, verified by replaying the exact case that crashed (now returns internally-consistent output). A live-browser E2E confirmation is still outstanding (no browser automation tool was available this session), but both pipeline-level blockers found this session are resolved.

The essay/criterion linking data-model incompatibility flagged below (kept for historical context) has been resolved by design and is now implemented, not just scoped.

Companion context: `CLAUDE.md`, `README.md`, `UI-DESIGN-HANDOFF.md`, `schema.sql` at repo root — all still current, read those first for full project background. This doc is additive, not a replacement.

---

## Resolved: essay/criterion linking model

**The problem** (unchanged from original scoping): frontend's `EssayChunk`/`EssayFixture` model (built 2026-08-11) assumed exactly one contiguous text chunk per criterion. Backend's actual output (decided 2026-08-12) is many-to-many — each criterion carries `sentence_refs: list[int]`, and citations can interleave (confirmed with real logged output: `bp2-evidence-2: sentence_refs=[12, 15]` sandwiches sentences cited by `bp2-reasoning-2: sentence_refs=[13, 14, 16]`). The old model has no way to represent this.

**The resolved model — sentence-centric, two independent lookup maps.**

A deterministic tokenizer (already decided 2026-08-13, not the LLM) produces a fixed, ordered sentence list. Two maps key off that same sentence index, because they answer two different questions:

- **`sectionOf`** — *geography*. Which of the 4 structural paragraphs (`thesis` / `bp1` / `bp2` / `conclusion`) a sentence renders in. Produced by the segmentation call. Roughly 1:1 (one section per sentence).
- **`citingCriteria`** — *purpose*. Which of the 14 rubric criteria cite this sentence, and therefore which in-essay tag chip(s) render before it. Produced by the grading calls' `sentence_refs`. Many-to-many (zero, one, or several criteria per sentence).

These are kept separate rather than derived from one another because a criterion with `sentence_refs: []` (missing) has nothing in `citingCriteria`, but still needs a section to structurally belong to — `sectionOf` is what preserves that even when `citingCriteria` has nothing to say.

```jsonc
{
  "sentences": [
    { "index": 12, "text": "The closing lines describe humanity born to keep striving..." },
    { "index": 13, "text": "That widened focus is doing real work..." },
    { "index": 14, "text": "...it belongs to anyone who has organized their life around a promise just out of reach." },
    { "index": 15, "text": "Fitzgerald reaches even further back, invoking the Dutch sailors..." },
    { "index": 16, "text": "Placed at the very end, that image reframes everything before it..." }
  ],
  "sectionOf": { "12": "bp2", "13": "bp2", "14": "bp2", "15": "bp2", "16": "bp2" },
  "citingCriteria": {
    "12": ["bp2-evidence-2"],
    "13": ["bp2-reasoning-2"],
    "14": ["bp2-reasoning-2"],
    "15": ["bp2-evidence-2"],
    "16": ["bp2-reasoning-2"]
  }
}
```

Rendering: group sentences by `sectionOf` into paragraphs; within each sentence, render a chip for every id in `citingCriteria[index]` (0, 1, or several) before the sentence text.

TS types for this shape are in `EssayLinking.types.ts` (see repo).

## Resolved: missing-criterion inline placement

**The problem**: a missing criterion (`sentence_refs: []`) has no entry in `citingCriteria`, so nothing tells the renderer where to drop the dashed inline placeholder chip the design spec requires (`UI-DESIGN-HANDOFF.md`: "the gap is visible on the page she's reading, not just summarized in a sidebar").

**The resolved rule**: infer placement from the rubric's fixed criterion order within the missing criterion's section (Claim → Evidence 1 → Reasoning 1 → Evidence 2 → Reasoning 2 → Synthesis for a body paragraph), not from `sectionOf` boundaries directly:

1. Find the immediately-preceding criterion in that fixed order for the same section.
2. Take the **last** sentence index in that preceding criterion's `sentence_refs`.
3. Insert the placeholder chip immediately after that sentence.
4. **Fallback**: if the missing criterion is first in its section's order (nothing precedes it — no realistic case today, since Claim is never missing in practice, but handle it defensively), insert at the start of the section's sentence range per `sectionOf`.

Worked example (`bp1-reasoning-1` missing, `bp1-evidence-1: sentence_refs=[1]`, `bp1-evidence-2: sentence_refs=[3]`): preceding criterion in order is `bp1-evidence-1`, last ref is sentence 1 → placeholder renders after sentence 1, before sentence 3 — reconstructing exactly where the reference mock hardcoded it, but now derived rather than hardcoded.

This was chosen over (a) dropping the inline placeholder entirely — rejected, it's a real spec requirement, not a nice-to-have — and (b) a coarse end-of-section marker — rejected, precise placement next to real anchor sentences is what lets her visually check the model's "missing" call against the actual text, which a coarse marker can't support.

Not yet handled: segmentation is explicitly best-effort and can misclassify a boundary sentence (`essays.segmentation_notes` exists for exactly this). Because insertion is anchored to `sentence_refs`, not to `sectionOf` boundaries, this rule is largely insulated from that — flagged as a residual edge case, not a blocker.

---

## Gap list

| Area | Current state | What's needed |
|---|---|---|
| **API client** | ~~Doesn't exist.~~ **Done (2026-08-14), request shape updated (2026-08-16).** `frontend/src/api/grade.ts` calls `POST /grade` with `{essay_text, assignment_prompt, class_id, student_name}` — `class_id` added 2026-08-16 (was missing entirely until then, see README's Decisions log). Response now also includes `essay_id` (2026-08-16), the anchor for dispute/resolve calls — threaded onto `GradedEssay.essayId`. | — |
| **Criterion shape** | Frontend's `RubricItem` wants `{id, label, group, score, missing, strengths, critiques, reasoning}`. Backend's `CriterionResult` returns `criterion_id` (not `id`), no `label`/`group`, plus extra fields the frontend doesn't model (`sentence_refs`, `confidence_level`, `confidence_reason`). | **Decided**: backend embeds `label`/`group` directly in the response (source of truth is `services/rubric.py`'s `RUBRIC` dict, already canonical) rather than the frontend maintaining a second copy. Field name aligns to `id` or frontend accepts `criterion_id` — pick one, cheap either way. |
| **Essay/criterion linking** | Was structurally incompatible. | **Resolved by design** — see "Resolved: essay/criterion linking model" above. Ready to implement. |
| **Missing-criterion placement** | Mock hardcoded a fixed insertion point; no positional anchor existed for `sentence_refs: []`. | **Resolved by design** — see "Resolved: missing-criterion inline placement" above. Ready to implement. |
| **Dispute flow** | ~~100% simulated client-side~~ **Done (2026-08-16).** `POST /grade/dispute` is a real conversational round-trip (`tool_choice: "auto"`, `services/dispute.py`) — note the re-grill vs. the original 2026-08-12 "re-runs its entire section call" design: `propose_revised_grade` now scopes to the single disputed criterion only, not all 6 section siblings (see README's 2026-08-16 Decisions log). `POST /grade/dispute/resolve` is a second new endpoint (Save correction/Keep original), also real — `GradedView.tsx`'s `saveCorrection`/`keepOriginal` call it instead of just setting local state. Both persist to Postgres (`disputes`/`dispute_messages`/`accepted_grades`, per the redesigned `schema.sql`). **Hardened same day**: `teacher_id`/`class_id` on the `disputes` row are derived server-side from the essay/session, not trusted from the request — `DisputeTurnRequest` no longer even has a `class_id` field. `POST /grade/dispute` returns 404/403 (`EssayNotFoundError`/`EssayAccessDeniedError`) if `essay_id` doesn't exist or belongs to a different teacher. `POST /grade/dispute/resolve` doesn't have this same ownership check yet — known gap. | — |
| **Session/setup** | ~~Frontend's `SetupScreen` caches `prompt`/`classId`/`selectedCriteria` in React state only, never sent anywhere.~~ **`class_id` closed 2026-08-16** — required on `GradeRequest`, persisted to `sessions.class_id`/`essays.teacher_id` via `database.persist_grading_run()`. **Still open**: criteria-subset selection has no backend effect yet — the backend always grades all 14 criteria regardless of `selectedCriteria`, and `sessions.criteria_selection` is hardcoded to `{"full_essay": true}` rather than reflecting a real per-criterion choice (partial-essay grading is explicitly unvalidated per CLAUDE.md's Deliberately deferred list). | Wire `selectedCriteria` through to `GradeRequest` and the pipeline if/when partial-essay grading is validated — not scoped yet. |
| **Transport** | No CORS middleware in `backend/src/aplit_grader/main.py`. No static-file serving of the built frontend from FastAPI. No Vite dev-server proxy config. | **Default for now**: CORS middleware for local dev (Vite on one port, FastAPI on another). Production shape (`frontend/dist` served as static assets from FastAPI, per README's Tech stack) can land later without blocking dev-time wiring. |

---

## What's already fine — don't re-audit this

Checked for drift against the markdown docs; no issues found in these areas:
- **Design tokens** (`frontend/src/index.css`) match `UI-DESIGN-HANDOFF.md`'s hex values exactly (chrome `#EDEAF6`, card `#3F3550`, paper `#FAF8F4`, tier colors, Petrona/Inter/Caveat fonts).
- **14-criterion structure** (Thesis + Body¶1×6 + Body¶2×6 + Conclusion) matches on both sides.
- **Missing-criterion visual treatment** (`!` badge, distinct copy) matches spec.
- **Autosave-vs-explicit-save principle** is correctly implemented in `DisputeThread.tsx` — `pickedScore` starts `null`, "Save correction" stays disabled until an explicit chip click, matching the documented fix over the reference mock's shortcut. Holds all the way to the backend now too (2026-08-16): `accepted_grades` is only ever written by `POST /grade/dispute/resolve`, which only fires on that explicit click — never on a `propose_revised_grade` tool call by itself.

---

## Suggested sequencing

1. ~~Resolve the essay/criterion linking data model~~ — **done, see above.**
2. Close the cheap criterion-shape gap (backend embeds `label`/`group`).
3. Add CORS middleware so a local dev request can physically reach the backend.
4. Implement the sentence-centric response shape server-side: segmentation call already produces the sentence list + section classification: it already has what it needs — expose `sentences`/`sectionOf` alongside the existing per-criterion `sentence_refs` (which becomes `citingCriteria` after a client- or server-side inversion) in the `/grade` response. Implement the missing-placement inference rule (client-side, since it's pure derivation from data already in the response — no new backend logic needed).
5. Build the real frontend types (`EssayLinking.types.ts`) and rendering loop (group by `sectionOf`, chip per `citingCriteria` entry, placeholder inference for `missing: true` criteria) replacing the old `EssayChunk`/`paras` rendering in `GradedView.tsx`.
6. Wire the real `POST /grade` call, replacing the `setTimeout` fixture path.
7. ~~Dispute flow and session/setup persistence remain bigger, separate efforts~~ — **done, 2026-08-16.** Both built same day as real Postgres persistence went in; see the Gap list rows above and README's Decisions log for full rationale. Remaining open item: criteria-subset selection still has no backend effect (see Session/setup row).
