import asyncio
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Protocol

from aplit_grader.schemas.requests import GradeResponse
from aplit_grader.services.pipeline import PipelineStepEvent


class ResultLogger(ABC):
    @abstractmethod
    async def log_step(self, run_id: str, event: PipelineStepEvent) -> None: ...

    @abstractmethod
    async def log_final_result(self, run_id: str, essay_text: str, result: GradeResponse) -> None: ...


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

    def _write(self, run_id: str, filename: str, body: dict[str, Any]) -> None:
        run_dir = self._base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / filename).write_text(json.dumps(body, indent=2))

    async def log_step(self, run_id: str, event: PipelineStepEvent) -> None:
        await asyncio.to_thread(self._write, run_id, f"{event.source}.json", _step_body(event))

    async def log_final_result(self, run_id: str, essay_text: str, result: GradeResponse) -> None:
        await asyncio.to_thread(
            self._write, run_id, "final_result.json", _final_result_body(essay_text, result)
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

    def _put(self, key: str, body: dict[str, Any]) -> None:
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=json.dumps(body, indent=2).encode(),
            ContentType="application/json",
        )

    async def log_step(self, run_id: str, event: PipelineStepEvent) -> None:
        await asyncio.to_thread(self._put, f"{run_id}/{event.source}.json", _step_body(event))

    async def log_final_result(self, run_id: str, essay_text: str, result: GradeResponse) -> None:
        await asyncio.to_thread(
            self._put, f"{run_id}/final_result.json", _final_result_body(essay_text, result)
        )
