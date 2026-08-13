import asyncio
from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass
from typing import Any, Literal

import anthropic

from aplit_grader.schemas.requests import GradeResponse
from aplit_grader.schemas.rubric import CriterionResult
from aplit_grader.services.body_paragraph import run_body_paragraph_call
from aplit_grader.services.conclusion import run_conclusion_call
from aplit_grader.services.inference import GradingModelClient, GradingModelError
from aplit_grader.services.segmentation import run_segmentation_call
from aplit_grader.services.thesis import run_thesis_call

PipelineSource = Literal["segmentation", "thesis", "body_1", "body_2", "conclusion"]

_RETRYABLE_EXCEPTIONS = (GradingModelError, anthropic.APIError)


@dataclass
class PipelineStepEvent:
    source: PipelineSource
    payload: dict[str, Any]
    model_version: str


OnStepComplete = Callable[[PipelineStepEvent], Awaitable[None]]


class PipelineAbortError(Exception):
    """Raised when a pipeline step fails after exhausting retries. Aborts the whole essay."""

    def __init__(self, failed_step: PipelineSource, original_error: Exception):
        super().__init__(f"Pipeline aborted at step '{failed_step}': {original_error}")
        self.failed_step = failed_step
        self.original_error = original_error


async def _call_with_retry[T](
    step_fn: Callable[[], Coroutine[Any, Any, T]],
    *,
    max_attempts: int,
    retry_backoff_seconds: float,
) -> T:
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return await step_fn()
        except _RETRYABLE_EXCEPTIONS as exc:
            last_exc = exc
            if attempt < max_attempts - 1 and retry_backoff_seconds > 0:
                await asyncio.sleep(retry_backoff_seconds)
    assert last_exc is not None
    raise last_exc


async def run_grading_pipeline(
    client: GradingModelClient,
    essay_text: str,
    assignment_prompt: str,
    *,
    on_step_complete: OnStepComplete | None = None,
    max_attempts: int = 2,
    retry_backoff_seconds: float = 1.0,
) -> GradeResponse:
    async def emit(source: PipelineSource, payload: dict[str, Any]) -> None:
        if on_step_complete is not None:
            await on_step_complete(
                PipelineStepEvent(source=source, payload=payload, model_version=client.model_version)
            )

    async def run_step[T](source: PipelineSource, step_fn: Callable[[], Coroutine[Any, Any, T]]) -> T:
        try:
            return await _call_with_retry(
                step_fn, max_attempts=max_attempts, retry_backoff_seconds=retry_backoff_seconds
            )
        except Exception as exc:
            raise PipelineAbortError(failed_step=source, original_error=exc) from exc

    segmentation = await run_step("segmentation", lambda: run_segmentation_call(client, essay_text))
    await emit(
        "segmentation",
        {
            "sentences": [s.model_dump() for s in segmentation.sentences],
            "segmentation_notes": segmentation.segmentation_notes,
        },
    )

    thesis_result = await run_step(
        "thesis",
        lambda: run_thesis_call(client, essay_text, segmentation.sentences, assignment_prompt),
    )
    await emit(
        "thesis",
        {
            "criterion": thesis_result.criterion.model_dump(),
            "extracted_thesis": thesis_result.extracted_thesis,
        },
    )

    body1_result = await run_step(
        "body_1",
        lambda: run_body_paragraph_call(
            client,
            essay_text,
            segmentation.sentences,
            paragraph_num=1,
            extracted_thesis=thesis_result.extracted_thesis,
            assignment_prompt=assignment_prompt,
        ),
    )
    await emit(
        "body_1",
        {
            "criteria": [c.model_dump() for c in body1_result.criteria],
            "coverage_summary": body1_result.coverage_summary,
        },
    )

    body2_result = await run_step(
        "body_2",
        lambda: run_body_paragraph_call(
            client,
            essay_text,
            segmentation.sentences,
            paragraph_num=2,
            extracted_thesis=thesis_result.extracted_thesis,
            assignment_prompt=assignment_prompt,
            prior_coverage_summary=body1_result.coverage_summary,
        ),
    )
    await emit(
        "body_2",
        {
            "criteria": [c.model_dump() for c in body2_result.criteria],
            "coverage_summary": body2_result.coverage_summary,
        },
    )

    conclusion_criterion = await run_step(
        "conclusion",
        lambda: run_conclusion_call(
            client,
            essay_text,
            segmentation.sentences,
            extracted_thesis=thesis_result.extracted_thesis,
            body1_coverage_summary=body1_result.coverage_summary,
            body2_coverage_summary=body2_result.coverage_summary,
            assignment_prompt=assignment_prompt,
        ),
    )
    await emit("conclusion", {"criterion": conclusion_criterion.model_dump()})

    all_criteria: list[CriterionResult] = (
        [thesis_result.criterion] + body1_result.criteria + body2_result.criteria + [conclusion_criterion]
    )

    return GradeResponse(
        criteria=all_criteria,
        sentences=segmentation.sentences,
        segmentation_notes=segmentation.segmentation_notes,
    )
