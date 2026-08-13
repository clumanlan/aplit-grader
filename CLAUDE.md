---
project: ap-lit-essay-grader
status: scoping
current_phase: 0
last_updated: 2026-08-12
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
Real-time, synchronous. Consumer: React (Vite) + TypeScript + Tailwind frontend, built to static assets and served by the FastAPI backend as one deployable (no split S3/CloudFront — no auth planned yet). Full flow, screens, and interaction patterns are designed — see UI-DESIGN-HANDOFF.md and the reference mock `ap-lit-grader-full-flow.jsx`. Latency budget: up to ~60-90s (scale-to-zero cold start), visible loading state required (real elapsed-time counter, not a fake progress bar).

## Data model
Six tables — see README.md "Data model" for full rationale and DDL. `sessions` (cached assignment setup: criteria selection, prompt, class) and `essays` (pasted text + student name) give the grade tables something to FK against — not in the original three-table sketch but required by it. `essay_sentences` (indexed sentence list, written by the segmentation call) is what makes span highlighting a lookup instead of a fuzzy string match: grading calls reference sentences by index, not raw character offsets or quoted text — offsets are computed server-side from this table. Then the original three: `raw_grades` (append-only, every model generation across all 5 calls; `source` distinguishes segmentation/thesis/body1/body2/conclusion/dispute-proposal; includes `confidence_level`/`confidence_reason` — set only on thesis rows), `accepted_grades` (append-only, latest-per-criterion wins, FK back to the `raw_grades` row it confirms/corrects — written only by explicit teacher action, never autosaved), `dispute_messages` (per-criterion discussion transcript). Agreement/override case classification falls out of comparing the two grade tables — no separate flag needed.

## Current phase

**Phase 0: Smallest end-to-end slice**
- Goal: Prove data → model → serving → consumer pipeline works, in parallel with learning QLoRA/DPO.
- Revised deliverable (2026-08-12): pipeline is being validated first against the **Claude API** (`claude-sonnet-5`) rather than self-hosted SageMaker — bare FastAPI (`POST /grade`) → Claude API → minimal frontend, tested on 3-5 real essays, results logged to S3 (no DB yet). This doubles as README's "Claude API zero-shot" baseline, so it isn't throwaway work. The model call sits behind a `GradingModelClient` interface (`AnthropicGradingClient` today) so a `SageMakerGradingClient` can be dropped in later without touching the API layer or rubric prompt-building code.
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

For rejected framings, data risks, leakage audit, system architecture diagram, cost estimates, and full rationale, see `README.md` at repo root. For the frontend design system, screen-by-screen flow, and API contract the UI expects, see `UI-DESIGN-HANDOFF.md`.
