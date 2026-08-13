import json

import pytest

from aplit_grader.schemas.requests import GradeResponse
from aplit_grader.schemas.rubric import CriterionResult
from aplit_grader.services.pipeline import PipelineStepEvent
from aplit_grader.storage.result_logger import LocalResultLogger, S3ResultLogger


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


class _FakeS3Client:
    def __init__(self):
        self.put_object_calls: list[dict] = []

    def put_object(self, **kwargs):
        self.put_object_calls.append(kwargs)


@pytest.mark.asyncio
async def test_local_logger_writes_a_json_file_per_step(tmp_path):
    logger = LocalResultLogger(base_dir=tmp_path)

    await logger.log_step("run-123", _sample_event())

    written = json.loads((tmp_path / "run-123" / "thesis.json").read_text())
    assert written["source"] == "thesis"
    assert written["model_version"] == "claude-sonnet-5-zeroshot"
    assert written["payload"]["extracted_thesis"] == "Hope is doomed."


@pytest.mark.asyncio
async def test_local_logger_creates_missing_run_directory(tmp_path):
    logger = LocalResultLogger(base_dir=tmp_path)

    await logger.log_step("brand-new-run", _sample_event())

    assert (tmp_path / "brand-new-run").is_dir()


@pytest.mark.asyncio
async def test_local_logger_writes_final_result_with_essay_text(tmp_path):
    logger = LocalResultLogger(base_dir=tmp_path)

    await logger.log_final_result("run-123", "The essay text.", _sample_result())

    written = json.loads((tmp_path / "run-123" / "final_result.json").read_text())
    assert written["essay_text"] == "The essay text."
    assert written["result"]["criteria"][0]["criterion_id"] == "thesis"


@pytest.mark.asyncio
async def test_s3_logger_puts_step_json_at_run_id_and_source_key():
    fake_s3 = _FakeS3Client()
    logger = S3ResultLogger(bucket="test-bucket", s3_client=fake_s3)

    await logger.log_step("run-123", _sample_event())

    assert len(fake_s3.put_object_calls) == 1
    call = fake_s3.put_object_calls[0]
    assert call["Bucket"] == "test-bucket"
    assert call["Key"] == "run-123/thesis.json"
    body = json.loads(call["Body"])
    assert body["source"] == "thesis"


@pytest.mark.asyncio
async def test_s3_logger_puts_final_result_at_run_id_key():
    fake_s3 = _FakeS3Client()
    logger = S3ResultLogger(bucket="test-bucket", s3_client=fake_s3)

    await logger.log_final_result("run-123", "The essay text.", _sample_result())

    call = fake_s3.put_object_calls[0]
    assert call["Key"] == "run-123/final_result.json"
    body = json.loads(call["Body"])
    assert body["essay_text"] == "The essay text."
