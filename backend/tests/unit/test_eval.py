import pytest

from aplit_grader.services.eval import evaluate_essay, format_report, run_eval
from aplit_grader.storage.result_logger import ResultLogger
from tests.fixtures.canned_pipeline_responses import happy_path_responses
from tests.fixtures.fake_grading_client import FakeGradingModelClient
from tests.fixtures.sample_essays import (
    GATSBY_ASSIGNMENT_PROMPT,
    GATSBY_FOUR_SENTENCE_ESSAY,
)


class _RecordingResultLogger(ResultLogger):
    def __init__(self):
        self.step_sources: list[str] = []
        self.final_results: list[str] = []

    async def log_step(self, run_id, event) -> None:
        self.step_sources.append(event.source)

    async def log_final_result(self, run_id, essay_text, result) -> None:
        self.final_results.append(run_id)


@pytest.mark.asyncio
async def test_evaluate_essay_succeeds_and_records_per_step_timing():
    client = FakeGradingModelClient(responses=happy_path_responses())
    logger = _RecordingResultLogger()

    result = await evaluate_essay(
        client, logger, "run-1", "essay_1", GATSBY_FOUR_SENTENCE_ESSAY, GATSBY_ASSIGNMENT_PROMPT
    )

    assert result.success is True
    assert result.essay_name == "essay_1"
    assert set(result.step_seconds) == {"segmentation", "thesis", "body_1", "body_2", "conclusion"}
    assert result.total_seconds >= 0
    assert logger.final_results == ["run-1"]


@pytest.mark.asyncio
async def test_evaluate_essay_reports_failure_without_raising():
    client = FakeGradingModelClient(response={"unexpected_shape": True})
    logger = _RecordingResultLogger()

    result = await evaluate_essay(
        client, logger, "run-1", "broken_essay", GATSBY_FOUR_SENTENCE_ESSAY, GATSBY_ASSIGNMENT_PROMPT
    )

    assert result.success is False
    assert "segmentation" in result.error
    assert logger.final_results == []


@pytest.mark.asyncio
async def test_run_eval_evaluates_every_essay_independently():
    client = FakeGradingModelClient(
        responses=happy_path_responses() + happy_path_responses()
    )
    logger = _RecordingResultLogger()

    results = await run_eval(
        client,
        logger,
        [("essay_1", GATSBY_FOUR_SENTENCE_ESSAY), ("essay_2", GATSBY_FOUR_SENTENCE_ESSAY)],
        GATSBY_ASSIGNMENT_PROMPT,
    )

    assert [r.essay_name for r in results] == ["essay_1", "essay_2"]
    assert all(r.success for r in results)


def test_format_report_includes_success_count_and_per_step_breakdown():
    from aplit_grader.services.eval import EssayEvalResult

    results = [
        EssayEvalResult(
            essay_name="essay_1",
            success=True,
            total_seconds=12.3,
            step_seconds={"segmentation": 2.1, "thesis": 3.0},
        ),
        EssayEvalResult(
            essay_name="essay_2",
            success=False,
            total_seconds=4.0,
            step_seconds={"segmentation": 4.0},
            error="aborted at thesis: boom",
        ),
    ]

    report = format_report(results)

    assert "essay_1" in report
    assert "essay_2" in report
    assert "1/2" in report
    assert "aborted at thesis: boom" in report


def test_format_report_warns_when_an_essay_exceeds_the_latency_budget():
    from aplit_grader.services.eval import EssayEvalResult

    results = [
        EssayEvalResult(
            essay_name="slow_essay", success=True, total_seconds=95.0, step_seconds={}
        )
    ]

    report = format_report(results)

    assert "90s" in report or "latency" in report.lower()
