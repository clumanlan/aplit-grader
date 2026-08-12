---
project: ap-lit-essay-grader
status: scoping
current_phase: 0
last_updated: 2026-08-11
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
Single fine-tuned 7-8B open-weight model, single-turn, structured generation: (essay, fixed rubric) → 14 per-section outputs, each `{ score: 1-4 | null, missing: bool, strengths: [], critiques: [], reasoning: string }`. Rubric structure: Thesis, Body ¶1 × 6 (Claim, Evidence 1, Reasoning 1, Evidence 2, Reasoning 2, Synthesis), Body ¶2 × same 6, Conclusion — NOT the ~10-criterion assumption from earlier scoping; each body paragraph has two evidence/reasoning pairs, not one. QLoRA via PEFT; DPO on her override triples, SFT on agreement triples. (See README.md for rejected framings — notably: this is NOT a holistic 0-6 score, that was a corrected early assumption.)

## Deployment shape
Real-time, synchronous. Consumer: React (Vite) + TypeScript + Tailwind frontend, built to static assets and served by the FastAPI backend as one deployable (no split S3/CloudFront — no auth planned yet). Full flow, screens, and interaction patterns are designed — see UI-DESIGN-HANDOFF.md and the reference mock `ap-lit-grader-full-flow.jsx`. Latency budget: up to ~60-90s (scale-to-zero cold start), visible loading state required (real elapsed-time counter, not a fake progress bar).

## Data model
Three tables, not one — see README.md "Data model" for full rationale: `raw_grades` (append-only, every model generation), `accepted_grades` (append-only, latest-per-criterion wins, FK back to the `raw_grades` row it confirms/corrects — written only by explicit teacher action, never autosaved), `dispute_messages` (per-criterion discussion transcript). Agreement/override case classification falls out of comparing the two grade tables — no separate flag needed.

## Current phase

**Phase 0: Smallest end-to-end slice**
- Goal: Prove data → model → serving → consumer pipeline works, in parallel with learning QLoRA/DPO. Zero-shot (no fine-tune) Qwen2.5-7B-Instruct AND Llama 3.1 8B on SageMaker real-time scale-to-zero GPU endpoints, hit by bare FastAPI + minimal frontend, tested on 3-5 real essays.
- Kill criteria: if SageMaker real-time scale-to-zero can't reliably host either model within a reasonable cold-start window, reassess hosting before proceeding.

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
