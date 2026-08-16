---
project: ap-lit-essay-grader
status: building
current_phase: 0
last_updated: 2026-08-16
---

# AP Lit Essay Grader — Claude Code Context

<!--
This file is auto-loaded by Claude Code at session start. Keep it lean (~50 lines).
Update the "Current phase" block as phases complete — Claude Code can review the
code itself to figure out what's finished, but should keep this file's "current_phase"
frontmatter and "Current phase" body section in sync as phases roll forward.
For full project context (rejected framings, data risks, system diagram, rationale),
see README.md. For the full frontend design system and interaction spec, see
UI-DESIGN-HANDOFF.md — the frontend is fully designed, not a placeholder.
-->

## End goal
Grade AP Lit essays per-section (14 criteria, 1-4 scale or flagged missing) against the real classroom rubric, with structured improvement feedback, replacing an ad-hoc Claude.ai grading workflow.

## Business metric
Weekly active usage (did she grade at least one essay this week). Secondary: time-per-essay, only trustworthy alongside override rate (falling time + rising override = rubber-stamping, a failure not a success).

## Chosen framing
**Re-grilled 2026-08-12** — was single-call, now a 5-call chained pipeline per essay (see README Decisions log for full rationale): (1) **segmentation call** — raw essay → structural sections + an indexed sentence list (essays don't reliably have exactly 4 paragraphs, so this is model-driven, not position-based) — (2) **thesis call** — grades Thesis, extracts (or reconstructs, if absent) the stated argument as context for downstream calls, plus a bucketed `confidence: high|medium|low` + `confidence_reason` (explicit-thesis-present / implied-across-sentences / not-found-at-all — NOT a raw numeric self-reported score, which research shows LLMs don't calibrate well) — (3) **Body ¶1 call** — grades against "supports the thesis," using the extracted thesis as context — (4) **Body ¶2 call** — grades against "completes the support" (not just relevance — coverage/redundancy vs. ¶1), using thesis + a summary of what ¶1 covered — (5) **Conclusion call** — graded as synthesis of both body paragraphs. Each grading call (2-5) returns 1+ of the 14 per-section outputs, each `{ score: 1-4 | null, missing: bool, strengths: [], critiques: [], reasoning: string }`; the thesis call additionally returns the confidence fields above. Chosen over one composite call because it matches the UI's independent per-criterion dispute threads (a disputed Evidence-1 score re-runs just the Body-¶1 call, not the whole essay) — full reasoning and the tradeoffs considered in README's Decisions log. Rubric structure: Thesis, Body ¶1 × 6 (Claim, Evidence 1, Reasoning 1, Evidence 2, Reasoning 2, Synthesis), Body ¶2 × same 6, Conclusion — NOT the ~10-criterion assumption from earlier scoping; each body paragraph has two evidence/reasoning pairs, not one. Fine-tuning target (Phase 1): QLoRA via PEFT; DPO on her override triples, SFT on agreement triples — her ~200 historical triples were one-shot, so **the segmentation+per-call structure is validated by re-grading a sample of historical essays and diffing against her actual decisions before being frozen for Phase 1 data collection**, not assumed correct on day one. (See README.md for rejected framings — notably: this is NOT a holistic 0-6 score, that was a corrected early assumption.)

## Deployment shape
Real-time, synchronous. Consumer: React (Vite) + TypeScript + Tailwind frontend, built to static assets and served by the FastAPI backend as one deployable (no split S3/CloudFront). Full flow, screens, and interaction patterns are designed — see UI-DESIGN-HANDOFF.md and the reference mock `ap-lit-grader-full-flow.jsx`. Latency budget: up to ~60-90s (scale-to-zero cold start), visible loading state required (real elapsed-time counter, not a fake progress bar).

**Auth (2026-08-15)**: Single-teacher Cognito sign-in, end to end — no multi-tenancy, this is one admin-created user. Frontend calls Cognito's `USER_PASSWORD_AUTH` flow directly over HTTPS (no AWS SDK dependency), handles the `NEW_PASSWORD_REQUIRED` challenge for first login, and holds the access token in memory only (`frontend/src/auth/authStore.ts` — not localStorage, cleared on refresh or a 401). Backend verifies the Cognito access token's signature against the pool's JWKS, issuer, and `client_id` claim (`backend/src/aplit_grader/api/auth.py`'s `get_current_teacher`), applied to every teacher-data route — currently just `POST /grade`, the only route that exists.

**Hosting (2026-08-15)**: Amazon ECS (Express Mode) — App Runner is off the table (closed to new customers 2026-04-30, and this account never created a service). Deploy is build image → push to ECR → Express Mode deploys from that image (a manual/CI step; there's no build-from-source flow like App Runner had). Express Mode sits in the default VPC, so RDS is private-only, reachable from the ECS service's security group — no public RDS endpoint. See README's Decisions log for the full rationale and the task-role/task-execution-role IAM split.

## Data model
Six tables — see README.md "Data model" for full rationale and DDL. `sessions` (cached assignment setup: criteria selection, prompt, class) and `essays` (pasted text + student name) give the grade tables something to FK against — not in the original three-table sketch but required by it. `essay_sentences` (indexed sentence list, written by the segmentation call) is what makes span highlighting a lookup instead of a fuzzy string match: grading calls reference sentences by index, not raw character offsets or quoted text — offsets are computed server-side from this table. Then the original three: `raw_grades` (append-only, every model generation across all 5 calls; `source` distinguishes segmentation/thesis/body1/body2/conclusion/dispute-proposal; includes `confidence_level`/`confidence_reason` — set only on thesis rows), `accepted_grades` (append-only, latest-per-criterion wins, FK back to the `raw_grades` row it confirms/corrects — written only by explicit teacher action, never autosaved), `dispute_messages` (per-criterion discussion transcript). Agreement/override case classification falls out of comparing the two grade tables — no separate flag needed.

## Current phase

**Phase 0: Smallest end-to-end slice**
- Goal: Prove data → model → serving → consumer pipeline works, in parallel with learning QLoRA/DPO.
- Revised deliverable (2026-08-12): pipeline validated first against the **Claude API** (`claude-sonnet-5`) rather than self-hosted SageMaker. This doubles as README's "Claude API zero-shot" baseline, so it isn't throwaway work.
- **Backend built and tested (2026-08-13)**: bare FastAPI (`POST /grade`) → 5-call pipeline → Claude API, results logged to S3/local via `ResultLogger` — 85 tests passing (unit/integration + 2 live tests against the real API). Validated end-to-end on 1 of the target 3-5 real essays (real API, real assignment prompt, all 14 criteria graded, within the 60-90s latency budget) — **not yet the full 3-5-essay validation this phase's deliverable calls for.** The model call sits behind a `GradingModelClient` interface (`AnthropicGradingClient` today) so a `SageMakerGradingClient` can be dropped in later without touching the API layer or rubric prompt-building code.
- **Frontend/backend connected (2026-08-14)**: real `POST /grade` API client (`frontend/src/api/grade.ts`) replaces the old fixture path; the sentence-centric essay/criterion linking model (`sectionOf`/`citingCriteria`, resolved 2026-08-13) is implemented on both sides — backend exposes `label`/`group`/`section_of`/`citing_criteria` via computed fields, frontend's `GradedView` renders sentence-by-sentence with inline chips and missing-criterion placement. 94 backend + 43 frontend tests passing, CORS wired for local dev.
- **Live-model reliability bug found and fixed (2026-08-14)**: 4 live-API smoke-test attempts hit two distinct pipeline failures. **Diagnosed and fixed**: the model occasionally double-encodes an array/object-typed tool-call field as a JSON string one level too deep (e.g. `{"sentence_sections": "{\"sentence_sections\":[...]}"}` instead of a native array) — the underlying answer (segmentation binning) was verified correct, just mis-wrapped; `services/inference.py`'s `generate_structured()` now repairs this per the tool's declared JSON Schema (`array`/`object` fields only, verified via 3 new unit tests, replayed against the live API against the exact essay that previously failed — now succeeds). **Second failure mode also diagnosed and fixed**: the `body_1` case (`missing: true` + non-null `score`) traced to root cause — none of the thesis/body-paragraph/conclusion system prompts or tool schemas ever explained what `missing` should mean versus a floor score of 1; the model was inferring it from the field name alone. Added `MISSING_FIELD_GUIDANCE` (`services/rubric.py`) — a shared instruction ("missing only when nothing addresses this criterion at all; weak/off-topic content is still scored, typically at 1") — to all three system prompts and to the `missing` field's JSON Schema `description` in all three tool schemas. Replayed the exact essay/step that crashed before: it now returns internally-consistent output (the previously-contradictory `bp1-claim` is `score=1, missing=False`; genuinely absent criteria are `score=None, missing=True`). Both live-API failure modes found this session are now fixed.
- **S3 result-log key structure fixed (2026-08-16)**: `S3ResultLogger`/`LocalResultLogger` were writing flat `{run_id}/{step}.json` keys straight to the bucket root. Restructured to `grading-runs/{teacher_id}/{class_slug}/{yyyy}/{mm}/{dd}/{run_id}/{step}.json` (`storage/result_logger.py`'s `RunContext` + `slugify_class_name`) — `teacher_id` is the Cognito `sub` from `get_current_teacher` (the real access boundary), `class_slug` is cosmetic/browsability-only. Also added explicit `ServerSideEncryption="AES256"` to `put_object`, and reserved `fine-tuning/`, `model-artifacts/`, `eval-results/` as sibling top-level prefixes. **Required threading `class_id` through `POST /grade` for the first time** — the frontend's `SetupScreen`/`Session.classId` already existed but was never actually sent to the backend; `GradeRequest.class_id` (required) and `GradeRequestPayload.classId` now close that gap. **RDS note**: `essays.s3_key` (nullable) added to `schema.sql`/the Alembic migration for Phase 1, but Phase 0 has no DB-write path at all (confirmed — no ORM/session code exists yet), so it can't actually be "populated on write" until Phase 1 wires real `essays`/`sessions` inserts into `POST /grade`. `sessions.assignment_prompt` already existed from the original schema — confirmed, no change needed.
- **Deferred, not eliminated**: Qwen2.5-7B-Instruct / Llama 3.1 8B on SageMaker real-time scale-to-zero GPU endpoints. Self-hosting setup (S3 model artifacts, endpoint config, inference-component autoscaling) is being done separately by the project owner, not in this backend build. The kill criteria below has NOT been evaluated yet and still gates Phase 1 — self-hosting is a prerequisite for the QLoRA/DPO fine-tuning plan, not an optional path.
- Kill criteria (still open): if SageMaker real-time scale-to-zero can't reliably host either model within a reasonable cold-start window, reassess hosting before proceeding to fine-tuning.

## Planned phases

- Phase 1: Grading + comments (single teacher) — fine-tune on ~200 real triples, ship the designed frontend, held-out eval (per-criterion QWK + adjacent-pair confusion matrices) vs. both baselines (Claude API zero-shot, base model zero-shot)
- Phase 2: Pseudonymous per-student progress tracking — no real names/school IDs, ever
- **Definition of done**: She can paste a real essay, get per-section scores + structured feedback within latency budget, her review (accept/discuss/correct) is captured with full dispute transcript, and held-out eval shows measurable adjacent-score-boundary improvement over baseline.

## Deliberately deferred

- Partial-essay grading (evidence-only, etc.): routed via prompt subset, but unvalidated — no training/eval coverage
- Multi-teacher rubric generalization, rubric-negotiation chat
- Second human grader / inter-rater ceiling
- Commercialization/selling (named as possible "next thing," not designed for now — no auth/multi-tenancy/billing)

---

For rejected framings, data risks, leakage audit, system architecture diagram, cost estimates, and full rationale, see `README.md` at repo root. For the frontend design system, screen-by-screen flow, and API contract the UI expects, see `UI-DESIGN-HANDOFF.md`. For measured per-step latency, token usage, and per-essay API cost against the live Claude API, see `MODEL-PERFORMANCE.md`.
