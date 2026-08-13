from typing import Any

import pytest

from aplit_grader.services.inference import GradingModelClient, GradingModelError
from aplit_grader.services.pipeline import (
    PipelineAbortError,
    PipelineStepEvent,
    run_grading_pipeline,
)
from aplit_grader.services.rubric import RUBRIC
from tests.fixtures.canned_pipeline_responses import (
    happy_path_responses as _happy_path_responses,
)
from tests.fixtures.canned_pipeline_responses import (
    segmentation_response as _segmentation_response,
)
from tests.fixtures.canned_pipeline_responses import thesis_response as _thesis_response
from tests.fixtures.fake_grading_client import FakeGradingModelClient
from tests.fixtures.sample_essays import GATSBY_ASSIGNMENT_PROMPT as ASSIGNMENT_PROMPT
from tests.fixtures.sample_essays import GATSBY_FOUR_SENTENCE_ESSAY as ESSAY_TEXT


class _FlakyThenQueueClient(GradingModelClient):
    """Fails the first `fail_first_n_calls` calls, then serves `responses` in order."""

    def __init__(self, responses: list[dict], fail_first_n_calls: int = 0):
        self._responses = list(responses)
        self._fail_first_n_calls = fail_first_n_calls
        self._calls_made = 0
        self.calls: list[dict[str, Any]] = []

    @property
    def model_version(self) -> str:
        return "flaky"

    async def generate_structured(self, **kwargs) -> dict:
        self.calls.append(kwargs)
        self._calls_made += 1
        if self._calls_made <= self._fail_first_n_calls:
            raise GradingModelError("simulated transient failure")
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_happy_path_returns_a_grade_response_covering_all_fourteen_criteria():
    client = FakeGradingModelClient(responses=_happy_path_responses())

    result = await run_grading_pipeline(client, ESSAY_TEXT, ASSIGNMENT_PROMPT, retry_backoff_seconds=0)

    assert {c.criterion_id for c in result.criteria} == set(RUBRIC)
    assert len(result.sentences) == 4
    assert result.segmentation_notes is None


@pytest.mark.asyncio
async def test_assignment_prompt_reaches_thesis_body_and_conclusion_calls():
    client = FakeGradingModelClient(responses=_happy_path_responses())

    await run_grading_pipeline(client, ESSAY_TEXT, ASSIGNMENT_PROMPT, retry_backoff_seconds=0)

    def calls_for(tool_name: str) -> list[dict]:
        return [c for c in client.calls if c["tool_name"] == tool_name]

    assert ASSIGNMENT_PROMPT in calls_for("submit_thesis_grade")[0]["user_prompt"]
    body_calls = calls_for("submit_body_paragraph_grades")
    assert len(body_calls) == 2  # BP1 and BP2
    assert all(ASSIGNMENT_PROMPT in c["user_prompt"] for c in body_calls)
    assert ASSIGNMENT_PROMPT in calls_for("submit_conclusion_grade")[0]["user_prompt"]


@pytest.mark.asyncio
async def test_on_step_complete_fires_once_per_step_in_order():
    client = FakeGradingModelClient(responses=_happy_path_responses())
    events: list[PipelineStepEvent] = []

    async def collect(event: PipelineStepEvent) -> None:
        events.append(event)

    await run_grading_pipeline(
        client, ESSAY_TEXT, ASSIGNMENT_PROMPT, on_step_complete=collect, retry_backoff_seconds=0
    )

    assert [e.source for e in events] == ["segmentation", "thesis", "body_1", "body_2", "conclusion"]
    assert all(e.model_version == "fake-model" for e in events)


@pytest.mark.asyncio
async def test_retries_a_transient_failure_once_before_succeeding():
    client = _FlakyThenQueueClient(_happy_path_responses(), fail_first_n_calls=1)

    result = await run_grading_pipeline(
        client, ESSAY_TEXT, ASSIGNMENT_PROMPT, max_attempts=2, retry_backoff_seconds=0
    )

    assert {c.criterion_id for c in result.criteria} == set(RUBRIC)
    assert len(client.calls) == 6  # 1 failed segmentation attempt + 5 successful calls


@pytest.mark.asyncio
async def test_aborts_the_whole_essay_after_exhausting_retries():
    client = _FlakyThenQueueClient(_happy_path_responses(), fail_first_n_calls=999)

    with pytest.raises(PipelineAbortError) as exc_info:
        await run_grading_pipeline(
            client, ESSAY_TEXT, ASSIGNMENT_PROMPT, max_attempts=2, retry_backoff_seconds=0
        )

    assert exc_info.value.failed_step == "segmentation"
    assert len(client.calls) == 2  # max_attempts=2, no later steps ever called


@pytest.mark.asyncio
async def test_on_step_complete_reflects_only_steps_that_succeeded_before_abort():
    # Segmentation and thesis succeed, body_1 fails permanently (every call after
    # the first 2 raises, rather than IndexError-ing off an exhausted queue).
    class _FailFromThirdCall(GradingModelClient):
        def __init__(self):
            self.calls: list[dict] = []
            self._responses = [_segmentation_response(), _thesis_response()]

        @property
        def model_version(self) -> str:
            return "fail-from-third"

        async def generate_structured(self, **kwargs) -> dict:
            self.calls.append(kwargs)
            if self._responses:
                return self._responses.pop(0)
            raise GradingModelError("body_1 permanently broken")

    client = _FailFromThirdCall()
    events: list[PipelineStepEvent] = []

    async def collect(event: PipelineStepEvent) -> None:
        events.append(event)

    with pytest.raises(PipelineAbortError) as exc_info:
        await run_grading_pipeline(
            client,
            ESSAY_TEXT,
            ASSIGNMENT_PROMPT,
            on_step_complete=collect,
            max_attempts=2,
            retry_backoff_seconds=0,
        )

    assert exc_info.value.failed_step == "body_1"
    assert [e.source for e in events] == ["segmentation", "thesis"]
