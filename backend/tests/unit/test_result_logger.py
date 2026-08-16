import json
from datetime import UTC, datetime

import pytest

from aplit_grader.schemas.requests import GradeResponse
from aplit_grader.schemas.rubric import CriterionResult
from aplit_grader.services.pipeline import PipelineStepEvent
from aplit_grader.storage.result_logger import (
    LocalResultLogger,
    RunContext,
    S3ResultLogger,
    slugify_class_name,
)


def _sample_event() -> PipelineStepEvent:
    return PipelineStepEvent(
        source="thesis",
        payload={"criterion": {"criterion_id": "thesis", "score": 3}, "extracted_thesis": "Hope is doomed."},
        model_version="claude-sonnet-5-zeroshot",
    )


def _sample_result() -> GradeResponse:
    criteria = [
        CriterionResult(
            criterion_id="thesis",
            score=3,
            missing=False,
            strengths=[],
            critiques=[],
            reasoning="...",
            sentence_refs=[],
        )
    ]
    return GradeResponse.model_construct(criteria=criteria, sentences=[], segmentation_notes=None)


def _sample_context(run_id: str = "run-123") -> RunContext:
    return RunContext(
        run_id=run_id,
        teacher_id="teacher-sub-abc",
        class_slug="period-3-ap-lit",
        started_at=datetime(2026, 8, 16, 12, 30, tzinfo=UTC),
    )


_EXPECTED_PREFIX = "grading-runs/teacher-sub-abc/period-3-ap-lit/2026/08/16/run-123"


class _FakeS3Client:
    def __init__(self):
        self.put_object_calls: list[dict] = []

    def put_object(self, **kwargs):
        self.put_object_calls.append(kwargs)


def test_slugify_class_name_normalizes_punctuation_and_case():
    assert slugify_class_name("Period 3 — AP Lit") == "period-3-ap-lit"


@pytest.mark.asyncio
async def test_local_logger_writes_a_json_file_per_step(tmp_path):
    logger = LocalResultLogger(base_dir=tmp_path)

    await logger.log_step(_sample_context(), _sample_event())

    written = json.loads((tmp_path / _EXPECTED_PREFIX / "thesis.json").read_text())
    assert written["source"] == "thesis"
    assert written["model_version"] == "claude-sonnet-5-zeroshot"
    assert written["payload"]["extracted_thesis"] == "Hope is doomed."


@pytest.mark.asyncio
async def test_local_logger_creates_missing_run_directory(tmp_path):
    logger = LocalResultLogger(base_dir=tmp_path)

    await logger.log_step(_sample_context("brand-new-run"), _sample_event())

    expected_dir = tmp_path / "grading-runs/teacher-sub-abc/period-3-ap-lit/2026/08/16/brand-new-run"
    assert expected_dir.is_dir()


@pytest.mark.asyncio
async def test_local_logger_writes_final_result_with_essay_text(tmp_path):
    logger = LocalResultLogger(base_dir=tmp_path)

    path = await logger.log_final_result(_sample_context(), "The essay text.", _sample_result())

    written = json.loads((tmp_path / _EXPECTED_PREFIX / "final_result.json").read_text())
    assert written["essay_text"] == "The essay text."
    assert written["result"]["criteria"][0]["criterion_id"] == "thesis"
    assert path == str(tmp_path / _EXPECTED_PREFIX / "final_result.json")


@pytest.mark.asyncio
async def test_s3_logger_puts_step_json_at_the_nested_grading_runs_key():
    fake_s3 = _FakeS3Client()
    logger = S3ResultLogger(bucket="test-bucket", s3_client=fake_s3)

    await logger.log_step(_sample_context(), _sample_event())

    assert len(fake_s3.put_object_calls) == 1
    call = fake_s3.put_object_calls[0]
    assert call["Bucket"] == "test-bucket"
    assert call["Key"] == f"{_EXPECTED_PREFIX}/thesis.json"
    assert call["ServerSideEncryption"] == "AES256"
    body = json.loads(call["Body"])
    assert body["source"] == "thesis"


@pytest.mark.asyncio
async def test_s3_logger_puts_final_result_at_the_nested_grading_runs_key():
    fake_s3 = _FakeS3Client()
    logger = S3ResultLogger(bucket="test-bucket", s3_client=fake_s3)

    key = await logger.log_final_result(_sample_context(), "The essay text.", _sample_result())

    call = fake_s3.put_object_calls[0]
    assert call["Key"] == f"{_EXPECTED_PREFIX}/final_result.json"
    assert call["ServerSideEncryption"] == "AES256"
    assert key == f"{_EXPECTED_PREFIX}/final_result.json"
    body = json.loads(call["Body"])
    assert body["essay_text"] == "The essay text."


@pytest.mark.asyncio
async def test_s3_logger_keys_different_teachers_and_classes_into_separate_prefixes():
    fake_s3 = _FakeS3Client()
    logger = S3ResultLogger(bucket="test-bucket", s3_client=fake_s3)
    other_context = RunContext(
        run_id="run-123",
        teacher_id="a-different-teacher-sub",
        class_slug="period-5-ap-lit",
        started_at=datetime(2026, 8, 16, 12, 30, tzinfo=UTC),
    )

    await logger.log_step(other_context, _sample_event())

    call = fake_s3.put_object_calls[0]
    assert call["Key"] == "grading-runs/a-different-teacher-sub/period-5-ap-lit/2026/08/16/run-123/thesis.json"
