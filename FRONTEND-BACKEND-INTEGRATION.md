# Frontend/Backend Integration — Gap Analysis

**Status as of 2026-08-13**: Backend Phase 0 build is complete and validated against the real Anthropic API on real essays. Frontend is complete and validated on its own (43 tests), built during a UI design session the day before backend architecture was finalized. **The two have never been connected — zero wiring exists.** This doc scopes the actual gap so the next session can pick up connection work without re-deriving it.

Companion context: `CLAUDE.md`, `README.md`, `UI-DESIGN-HANDOFF.md`, `schema.sql` at repo root — all still current, read those first for full project background. This doc is additive, not a replacement.

---

## The core problem: essay/criterion linking model mismatch

This is the one gap that's a real design problem, not just wiring, and it should be resolved before attempting to connect the two sides.

**Frontend's model** (`frontend/src/components/GradedView.tsx`), built 2026-08-11:
```ts
interface EssayChunk { id: string; text?: string; missing?: boolean }
interface EssayFixture { title: string; paras: EssayChunk[][] }
```
This assumes: exactly one contiguous text chunk per criterion, arranged into exactly 4 fixed paragraphs, each chunk keyed by a single criterion `id`.

**Backend's actual model** (`schema.sql`, `services/rubric.py`, `schemas/rubric.py`), decided 2026-08-12 — one day *after* the frontend was built:
- Essays are split into however many sentences the deterministic splitter finds (not tied to a fixed paragraph count — CLAUDE.md: "essays don't reliably have exactly 4 paragraphs").
- Each of the 14 criteria carries its own `sentence_refs: list[int]` — zero, one, or many sentence indices.
- Sentences and criteria are **many-to-many**, not 1:1.

**This isn't theoretical — confirmed with real logged output** (`backend/grading_results/`):
```
bp2-evidence-2   sentence_refs=[12, 15]
bp2-reasoning-2  sentence_refs=[13, 14, 16]
```
Sentence 15 (Evidence 2) sits between two Reasoning 2 sentences. The frontend's chunk model has no way to represent this — a criterion citing non-adjacent sentences, or a sentence's "owner" not being a single clean value.

**Also unsolved**: where does a missing criterion's placeholder render inline? The design mock hardcodes a fixed insertion point between two specific chunks (`UI-DESIGN-HANDOFF.md`'s "dashed, outlined placeholder chip... between Evidence 1 and Evidence 2 in the mock"). The real backend has no positional anchor for a criterion with `sentence_refs: []` — there's nothing to point at. Backend's `services/report.py` (a dev-only tool, not the real UI) sidesteps this by never trying to place missing criteria inline at all — it just shows them in the criterion-card list. The real frontend's spec requires an inline placeholder, and nobody has designed how to compute where that goes yet.

**Recommendation**: resolve this data-model question — likely a redesigned `EssayFixture` shape built around the sentence list + a `sentence_index → citing criteria[]` map (same shape `services/report.py` already uses successfully, see `_sentence_criterion_map` in `backend/src/aplit_grader/services/report.py`) — before writing any frontend fetch code. Wiring an API call to a data shape that can't represent real model output just relocates the problem.

---

## Gap list

| Area | Current state | What's needed |
|---|---|---|
| **API client** | Doesn't exist. `frontend/src/App.tsx`'s `handleGradeEssay` calls `startGrading()`, which just `setTimeout`s for 3s then renders the hardcoded `DEMO_RUBRIC`/`DEMO_ESSAY` fixture regardless of what was pasted. | A real `fetch`/client layer calling `POST /grade` with `{essay_text, assignment_prompt, student_name}`. |
| **Criterion shape** | Frontend's `RubricItem` wants `{id, label, group, score, missing, strengths, critiques, reasoning}`. Backend's `CriterionResult` returns `criterion_id` (not `id`), no `label`/`group` (those live in `backend/src/aplit_grader/services/rubric.py`'s `RUBRIC` dict), plus extra fields the frontend doesn't model (`sentence_refs`, `confidence_level`, `confidence_reason`). | Cheap to close — frontend already hardcodes an id→label/group map (`SETUP_CRITERIA` in `App.tsx`); either reuse that client-side or have the backend embed label/group in the response. |
| **Essay/criterion linking** | See above — structurally incompatible models. | Redesign, see recommendation above. |
| **Missing-criterion placement** | Mock hardcodes a fixed insertion point. Backend has no positional anchor for `sentence_refs: []`. | Needs a design decision, not just code — e.g., could infer a plausible insertion point from surrounding sentence indices in the same section, or change the UI treatment to not require inline placement. |
| **Dispute flow** | 100% simulated client-side in `GradedView.tsx` (`setTimeout` + canned reply text, proposed score = `effScore(id) - 1`). No dispute endpoints exist on the backend at all. | A new API route wrapping the dispute re-run behavior. The 4 grading-call functions (`services/thesis.py`, `body_paragraph.py`, `conclusion.py`, `segmentation.py`) are already independently callable by design for exactly this — see README's Decisions log 2026-08-12 "dispute scope" entry (disputing one criterion re-runs its *entire section call*, not just that criterion) — but no HTTP layer or dispute-message persistence exists yet (Phase 0 has no DB, per CLAUDE.md). |
| **Session/setup** | Frontend's `SetupScreen` caches `prompt`/`classId`/`selectedCriteria` in React state only, never sent anywhere. | Backend's `GradeRequest` only takes `essay_text` + `assignment_prompt` + optional `student_name` per single request — no session concept, no criteria-subset grading (backend always grades all 14; partial-essay grading is explicitly unvalidated per CLAUDE.md's Deliberately deferred list). |
| **Transport** | No CORS middleware in `backend/src/aplit_grader/main.py`. No static-file serving of the built frontend from FastAPI. No Vite dev-server proxy config. | Either add CORS middleware for local dev (Vite on one port, FastAPI on another), or wire up serving `frontend/dist` as static assets from FastAPI per the intended one-deployable production shape (`CLAUDE.md`'s Deployment shape) — the latter avoids needing CORS in prod but doesn't solve local dev by itself. |

---

## What's already fine — don't re-audit this

Checked for drift against the markdown docs; no issues found in these areas:
- **Design tokens** (`frontend/src/index.css`) match `UI-DESIGN-HANDOFF.md`'s hex values exactly (chrome `#EDEAF6`, card `#3F3550`, paper `#FAF8F4`, tier colors, Petrona/Inter/Caveat fonts).
- **14-criterion structure** (Thesis + Body¶1×6 + Body¶2×6 + Conclusion) matches on both sides.
- **Missing-criterion visual treatment** (`!` badge, distinct copy) matches spec.
- **Autosave-vs-explicit-save principle** is correctly implemented in `DisputeThread.tsx` — `pickedScore` starts `null`, "Save correction" stays disabled until an explicit chip click, matching the documented fix over the reference mock's shortcut.

---

## Suggested sequencing (not a decision, just a starting point)

1. Resolve the essay/criterion linking data model (design question, see above) — blocks everything downstream that touches the essay view.
2. Close the cheap criterion-shape gap (id/label/group).
3. Add CORS or static serving so a request can physically reach the backend.
4. Wire the real `POST /grade` call, replacing the `setTimeout` fixture path.
5. Dispute flow and session/setup persistence are bigger, separate efforts — likely worth their own scoping pass once the above is working end-to-end on a real essay through the real UI.
