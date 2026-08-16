import asyncio
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from aplit_grader.schemas.requests import GradeResponse
from aplit_grader.services.pipeline import PipelineStepEvent

# Top-level bucket prefixes. grading-runs/ is the only one written today; the rest
# are reserved for Phase 1+ so future writers don't collide with this layout:
#   fine-tuning/datasets/{raw,train,eval}/
#   fine-tuning/runs/{run_id}/
#   model-artifacts/{model_name}/{version}/
#   eval-results/{run_id}/
GRADING_RUNS_PREFIX = "grading-runs"


def slugify_class_name(class_name: str) -> str:
    """Lowercase, key-safe slug for S3 path organization only — never an access boundary."""
    normalized = re.sub(r"[^a-z0-9]+", "-", class_name.strip().lower())
    return normalized.strip("-")


@dataclass(frozen=True)
class RunContext:
    """Identifies a single grading run for logging — who ran it, for which class, when."""

    run_id: str
    teacher_id: str
    class_slug: str
    started_at: datetime  # UTC


def _run_key_prefix(context: RunContext) -> str:
    d = context.started_at
    return (
        f"{GRADING_RUNS_PREFIX}/{context.teacher_id}/{context.class_slug}/"
        f"{d:%Y}/{d:%m}/{d:%d}/{context.run_id}"
    )


class ResultLogger(ABC):
    @abstractmethod
    async def log_step(self, context: RunContext, event: PipelineStepEvent) -> None: ...

    @abstractmethod
    async def log_final_result(
        self, context: RunContext, essay_text: str, result: GradeResponse
    ) -> str:
        """Returns the location (path or S3 key) the final result was written to."""
        ...


def _step_body(event: PipelineStepEvent) -> dict[str, Any]:
    return {
        "source": event.source,
        "payload": event.payload,
        "model_version": event.model_version,
    }


def _final_result_body(essay_text: str, result: GradeResponse) -> dict[str, Any]:
    return {
        "essay_text": essay_text,
        "result": result.model_dump(),
    }


class LocalResultLogger(ResultLogger):
    def __init__(self, base_dir: str | Path):
        self._base_dir = Path(base_dir)

    def _write(self, context: RunContext, filename: str, body: dict[str, Any]) -> str:
        run_dir = self._base_dir / _run_key_prefix(context)
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / filename
        path.write_text(json.dumps(body, indent=2))
        return str(path)

    async def log_step(self, context: RunContext, event: PipelineStepEvent) -> None:
        await asyncio.to_thread(self._write, context, f"{event.source}.json", _step_body(event))

    async def log_final_result(
        self, context: RunContext, essay_text: str, result: GradeResponse
    ) -> str:
        return await asyncio.to_thread(
            self._write, context, "final_result.json", _final_result_body(essay_text, result)
        )


class _S3Client(Protocol):
    def put_object(self, **kwargs: Any) -> Any: ...


class S3ResultLogger(ResultLogger):
    def __init__(self, bucket: str, *, s3_client: _S3Client | None = None):
        self._bucket = bucket
        if s3_client is not None:
            self._client = s3_client
        else:
            import boto3

            self._client = boto3.client("s3")

    def _put(self, key: str, body: dict[str, Any]) -> str:
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=json.dumps(body, indent=2).encode(),
            ContentType="application/json",
            ServerSideEncryption="AES256",
        )
        return key

    async def log_step(self, context: RunContext, event: PipelineStepEvent) -> None:
        key = f"{_run_key_prefix(context)}/{event.source}.json"
        await asyncio.to_thread(self._put, key, _step_body(event))

    async def log_final_result(
        self, context: RunContext, essay_text: str, result: GradeResponse
    ) -> str:
        key = f"{_run_key_prefix(context)}/final_result.json"
        return await asyncio.to_thread(self._put, key, _final_result_body(essay_text, result))
