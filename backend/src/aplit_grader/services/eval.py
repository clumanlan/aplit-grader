import time
from dataclasses import dataclass, field

from aplit_grader.services.inference import GradingModelClient
from aplit_grader.services.pipeline import (
    PipelineAbortError,
    PipelineStepEvent,
    run_grading_pipeline,
)
from aplit_grader.storage.result_logger import ResultLogger

LATENCY_BUDGET_SECONDS = 90.0


@dataclass
class EssayEvalResult:
    essay_name: str
    success: bool
    total_seconds: float
    step_seconds: dict[str, float] = field(default_factory=dict)
    error: str | None = None


async def evaluate_essay(
    client: GradingModelClient,
    logger: ResultLogger,
    run_id: str,
    essay_name: str,
    essay_text: str,
    assignment_prompt: str,
) -> EssayEvalResult:
    start = time.monotonic()
    last_ts = start
    step_seconds: dict[str, float] = {}

    async def on_step_complete(event: PipelineStepEvent) -> None:
        nonlocal last_ts
        now = time.monotonic()
        step_seconds[event.source] = now - last_ts
        last_ts = now
        await logger.log_step(run_id, event)

    try:
        result = await run_grading_pipeline(
            client, essay_text, assignment_prompt, on_step_complete=on_step_complete
        )
    except PipelineAbortError as exc:
        return EssayEvalResult(
            essay_name=essay_name,
            success=False,
            total_seconds=time.monotonic() - start,
            step_seconds=step_seconds,
            error=f"aborted at {exc.failed_step}: {exc.original_error}",
        )

    await logger.log_final_result(run_id, essay_text, result)
    return EssayEvalResult(
        essay_name=essay_name,
        success=True,
        total_seconds=time.monotonic() - start,
        step_seconds=step_seconds,
    )


async def run_eval(
    client: GradingModelClient,
    logger: ResultLogger,
    essays: list[tuple[str, str]],
    assignment_prompt: str,
) -> list[EssayEvalResult]:
    results = []
    for essay_name, essay_text in essays:
        run_id = f"{essay_name}-{int(time.time() * 1000)}"
        results.append(
            await evaluate_essay(client, logger, run_id, essay_name, essay_text, assignment_prompt)
        )
    return results


def format_report(results: list[EssayEvalResult]) -> str:
    lines = []
    for r in results:
        status = "OK" if r.success else f"FAILED ({r.error})"
        lines.append(f"{r.essay_name}: {status} — {r.total_seconds:.1f}s total")
        for source, seconds in r.step_seconds.items():
            lines.append(f"    {source}: {seconds:.1f}s")

    n_success = sum(1 for r in results if r.success)
    lines.append(f"\n{n_success}/{len(results)} essays graded successfully")

    over_budget = [r for r in results if r.success and r.total_seconds > LATENCY_BUDGET_SECONDS]
    if over_budget:
        names = ", ".join(r.essay_name for r in over_budget)
        lines.append(
            f"WARNING: {len(over_budget)} essay(s) exceeded the {LATENCY_BUDGET_SECONDS:.0f}s "
            f"latency budget: {names}"
        )

    return "\n".join(lines)
