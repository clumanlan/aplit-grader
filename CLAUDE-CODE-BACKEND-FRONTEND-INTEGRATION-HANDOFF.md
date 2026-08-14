# Handoff: Frontend/Backend Connection — 2026-08-13

Read this before touching integration code. It closes the one open design
question from `FRONTEND-BACKEND-INTEGRATION.md` — everything below is decided,
not proposed. Full rationale for the two big decisions lives in that doc's
"Resolved:" sections; this file is the short version plus what's left to
actually build.

## Decided this session

1. **Essay/criterion linking** — sentence-centric model. Deterministic
   tokenizer (already built, per README's 2026-08-13 decision) produces a
   fixed `sentences[]` list. Two independent maps key off sentence index:
   `sectionOf` (segmentation call output — which of the 4 paragraphs) and
   `citingCriteria` (derived from each criterion's `sentence_refs` — which
   criteria cite this sentence, many-to-many, can be empty). Replaces the old
   `EssayChunk`/`EssayFixture` shape entirely. Types: `EssayLinking.types.ts`.
2. **Missing-criterion inline placement** — inferred from fixed rubric order
   within the criterion's section, anchored to the last sentence index of the
   immediately-preceding criterion (fallback: start of section if nothing
   precedes it). Implemented as `resolveMissingPlacement()` in
   `EssayLinking.types.ts` — pure client-side derivation, no new backend logic
   required.
3. **Criterion shape** — backend embeds `label`/`group` in each criterion
   response (source of truth stays `services/rubric.py`'s `RUBRIC` dict, not a
   duplicated frontend map).
4. **Transport for now** — CORS middleware for local dev. Static-file serving
   of `frontend/dist` from FastAPI (the intended prod shape per README) can
   come later and isn't a blocker for wiring.

## What to actually build, in order

1. Backend: embed `label`/`group` in `CriterionResult` responses (align
   `criterion_id` → `id` or update frontend to read `criterion_id`, either is
   fine, just pick one and be consistent).
2. Backend: add CORS middleware for local dev.
3. Backend: expose `sentences` and `sectionOf` in the `/grade` response — the
   segmentation call already computes both; they just aren't surfaced today.
   `citingCriteria` can either be sent precomputed (backend already builds an
   equivalent map in `services/report.py`'s `_sentence_criterion_map` — reuse
   it) or derived client-side via `buildCitingCriteria()` in
   `EssayLinking.types.ts`. Prefer precomputed if cheap; either is correct.
4. Frontend: replace `GradedView.tsx`'s `EssayChunk`/`paras` rendering with the
   sentence-centric loop — group `sentences` by `sectionOf` into paragraphs,
   render a chip per `citingCriteria[index]` entry before each sentence, use
   `resolveMissingPlacement()` to drop the dashed placeholder chip for any
   criterion with `missing: true`.
5. Frontend: write the real API client (`fetch` to `POST /grade`), replace the
   `setTimeout` + `DEMO_RUBRIC` fixture path in `App.tsx`'s
   `handleGradeEssay`/`startGrading`.
6. Manual smoke test: paste a real essay through the real UI end-to-end,
   confirm scores/chips/placeholder land correctly, including a check against
   the known interleaving case (Evidence 2 / Reasoning 2 in either body
   paragraph) if the test essay happens to produce one.

## Explicitly not in scope for this pass

Dispute flow (needs new backend routes + `dispute_messages` persistence) and
session/setup persistence (`classId` has no backend consumer until Phase 2;
criteria-subset selection has no backend effect yet — backend always grades
all 14) are separate, larger efforts. Don't fold them into this connection
work — see `FRONTEND-BACKEND-INTEGRATION.md`'s gap list for their own scoping
notes when it's time.

## Files changed/added this session

- `FRONTEND-BACKEND-INTEGRATION.md` — updated with resolved design + revised
  sequencing.
- `EssayLinking.types.ts` — new. Types + `buildCitingCriteria()` +
  `resolveMissingPlacement()`, ready to drop into `frontend/src/`.
