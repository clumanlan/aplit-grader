import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException

from aplit_grader.api.auth import TeacherIdentity, get_current_teacher
from aplit_grader.config import Settings, get_settings
from aplit_grader.schemas.requests import GradeRequest, GradeResponse
from aplit_grader.services.inference import AnthropicGradingClient, GradingModelClient
from aplit_grader.services.pipeline import (
    PipelineAbortError,
    PipelineStepEvent,
    run_grading_pipeline,
)
from aplit_grader.storage.result_logger import (
    LocalResultLogger,
    ResultLogger,
    RunContext,
    S3ResultLogger,
    slugify_class_name,
)

router = APIRouter()


def get_grading_client(settings: Settings = Depends(get_settings)) -> GradingModelClient:
    return AnthropicGradingClient(model=settings.grading_model_version)


def get_result_logger(settings: Settings = Depends(get_settings)) -> ResultLogger:
    if settings.result_logger_backend == "s3":
        if not settings.s3_bucket:
            raise RuntimeError("S3_BUCKET must be set when RESULT_LOGGER_BACKEND=s3")
        return S3ResultLogger(bucket=settings.s3_bucket)
    return LocalResultLogger(base_dir=settings.result_logger_local_dir)


@router.post("/grade", response_model=GradeResponse)
async def grade_essay(
    request: GradeRequest,
    teacher: TeacherIdentity = Depends(get_current_teacher),
    client: GradingModelClient = Depends(get_grading_client),
    logger: ResultLogger = Depends(get_result_logger),
) -> GradeResponse:
    run_context = RunContext(
        run_id=str(uuid.uuid4()),
        teacher_id=teacher.sub,
        class_slug=slugify_class_name(request.class_id),
        started_at=datetime.now(UTC),
    )

    async def on_step_complete(event: PipelineStepEvent) -> None:
        await logger.log_step(run_context, event)

    try:
        result = await run_grading_pipeline(
            client, request.essay_text, request.assignment_prompt, on_step_complete=on_step_complete
        )
    except PipelineAbortError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "grading_pipeline_failed",
                "failed_step": exc.failed_step,
                "message": str(exc.original_error),
            },
        ) from exc

    await logger.log_final_result(run_context, request.essay_text, result)
    return result
