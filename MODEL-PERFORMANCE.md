# Model Performance — AP Lit Essay Grader

Measured operational characteristics of the 5-call grading pipeline against the live Claude API (`claude-sonnet-5`). This is a living doc — append new measurement runs rather than replacing the numbers below, so trends across essays/model versions are visible over time.

**Baseline run**: 2026-08-14, real essay (`sample_essay.txt`, a genuine unpolished student essay on Brooks' "kitchenette building" — not a toy/synthetic essay), real prompt (`sample_prompt.txt`), single run. n=1 — not yet a statistical sample; treat as a first data point, not a guarantee.

## Latency

| Step | Time | % of total |
|---|---|---|
| segmentation | 3.60s | 5% |
| thesis | 7.53s | 11% |
| body_1 | 22.00s | 31% |
| body_2 | 26.12s | 37% |
| conclusion | 11.16s | 16% |
| **TOTAL** | **70.41s** | 100% |

Falls inside the documented 60-90s latency budget (`CLAUDE.md`). Body ¶1 and ¶2 dominate (68% combined) because each grades 6 criteria with real reasoning, not 1 — and ¶2 additionally has to read ¶1's coverage summary to judge redundancy.

**This will not get faster on repeat requests within a session.** Unlike the original SageMaker scale-to-zero plan this budget was first written for, the Claude API has no cold start — every essay pays the full 5-call sequential cost, every time. The calls are sequential by real design, not accident: `thesis` needs `segmentation`'s sentence list, `body_1` needs the extracted thesis, `body_2` needs the thesis *and* `body_1`'s coverage summary, `conclusion` needs both body summaries. Collapsing this back to parallel calls would mean giving up the cross-paragraph awareness that's the actual point of the chained design (README's 2026-08-12 Decisions log entry).

## Token usage & cost per step

Same run, `claude-sonnet-5` pricing: $2.00/$10.00 per MTok (input/output) at the introductory rate through 2026-08-31, $3.00/$15.00 standard rate after.

| Step | Input tokens | Output tokens | Cost (intro) | Cost (standard) |
|---|---|---|---|---|
| segmentation | 1,891 | 430 | $0.0081 | $0.0121 |
| thesis | 2,528 | 754 | $0.0126 | $0.0189 |
| body_1 | 3,801 | 2,259 | $0.0302 | $0.0453 |
| body_2 | 4,391 | 2,644 | $0.0352 | $0.0528 |
| conclusion | 3,259 | 1,029 | $0.0168 | $0.0252 |
| **TOTAL** | **15,870** | **7,116** | **≈$0.10** | **≈$0.15** |

At this rate, grading 200 essays (the size of the teacher's historical triple set, per README) costs roughly $20-30 in API spend — well inside the "not a meaningful constraint" framing of README's existing Cost estimate section (which covers projected SageMaker infra cost for Phase 1, not this Phase 0 per-request API cost — this table is the piece that section was missing).

## How to reproduce

```python
import asyncio, time
import aplit_grader.config
from aplit_grader.services.inference import AnthropicGradingClient
from aplit_grader.services.pipeline import run_grading_pipeline

essay_text = open("sample_essay.txt").read().strip()
assignment_prompt = open("sample_prompt.txt").read().strip()

async def main():
    client = AnthropicGradingClient(model="claude-sonnet-5")
    real_create = client._client.messages.create
    usage_log = []
    async def wrapped_create(*args, **kwargs):
        resp = await real_create(*args, **kwargs)
        usage_log.append((resp.usage.input_tokens, resp.usage.output_tokens))
        return resp
    client._client.messages.create = wrapped_create

    timings, last = {}, {"t": None}
    async def on_step_complete(event):
        now = time.monotonic()
        timings[event.source] = now - last["t"]
        last["t"] = now

    start = time.monotonic()
    last["t"] = start
    await run_grading_pipeline(client, essay_text, assignment_prompt, on_step_complete=on_step_complete)
    total = time.monotonic() - start

    for step, (inp, out) in zip(timings.keys(), usage_log):
        print(f"{step:12s} time={timings[step]:6.2f}s  input={inp:5d}  output={out:4d}")
    print(f"TOTAL time={total:.2f}s")

asyncio.run(main())
```

Run from `backend/` with `uv run python3 -c "..."` (or save as a script). Requires `ANTHROPIC_API_KEY` in `backend/.env`.

## Reliability (not yet a statistical sample, but worth tracking)

Two live-API structured-output failure modes were found and fixed on 2026-08-14 — see `CLAUDE.md`'s Current phase section and README's Decisions log for full detail:

1. **Segmentation double-encoding** — the model occasionally wraps an array-typed tool field as a JSON string one level too deep. Fixed generically in `services/inference.py`.
2. **`missing`/`score` inconsistency** — the model sometimes flagged a criterion `missing: true` while also giving it a real score, because no prompt explained the distinction. Fixed by adding `MISSING_FIELD_GUIDANCE` to all three grading prompts (`services/rubric.py`).

Both were reproduced and confirmed fixed by replaying the exact failing case. No live failures observed since. Worth appending a note here if either recurs, or if a new failure mode is found — this file and the reliability section of `CLAUDE.md` should stay in sync.

## Open items

- n=1 essay measured so far — no distribution across the 3-5 essays Phase 0's deliverable calls for, or across essay length/complexity
- No measurement yet against a `missing`-heavy essay (all runs so far graded fairly complete essays) or a very short one
- No comparison point yet against a self-hosted Qwen2.5-7B/Llama 3.1 8B (Phase 1) — this table is the Claude-API-zero-shot baseline those will eventually be measured against
