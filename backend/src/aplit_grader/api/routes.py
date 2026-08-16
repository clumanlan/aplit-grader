import uuid
from datetime import UTC, datetime
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException

from aplit_grader.api.auth import TeacherIdentity, get_current_teacher
from aplit_grader.config import Settings, get_settings
from aplit_grader.schemas.requests import (
    DisputeResolveRequest,
    DisputeResolveResponse,
    DisputeTurnRequest,
    DisputeTurnResponse,
    GradeRequest,
    GradeResponse,
)
from aplit_grader.services.dispute import run_dispute_turn
from aplit_grader.services.inference import (
    AnthropicGradingClient,
    GradingModelClient,
    GradingModelError,
)
from aplit_grader.services.pipeline import (
    PipelineAbortError,
    PipelineStepEvent,
    run_grading_pipeline,
)
from aplit_grader.storage.db import (
    Database,
    DisputeNotFoundError,
    EssayAccessDeniedError,
    EssayNotFoundError,
    RawGradeMismatchError,
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


@lru_cache
def _get_database(database_url: str) -> Database:
    return Database(database_url)


def get_database(settings: Settings = Depends(get_settings)) -> Database:
    return _get_database(settings.database_url)


@router.post("/grade", response_model=GradeResponse)
async def grade_essay(
    request: GradeRequest,
    teacher: TeacherIdentity = Depends(get_current_teacher),
    client: GradingModelClient = Depends(get_grading_client),
    logger: ResultLogger = Depends(get_result_logger),
    database: Database = Depends(get_database),
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

    s3_key = await logger.log_final_result(run_context, request.essay_text, result)

    essay_id = await database.persist_grading_run(
        run_id=run_context.run_id,
        teacher_id=teacher.sub,
        class_id=request.class_id,
        assignment_prompt=request.assignment_prompt,
        student_name=request.student_name,
        essay_text=request.essay_text,
        segmentation_notes=result.segmentation_notes,
        s3_key=s3_key,
        criteria=result.criteria,
        model_version=client.model_version,
    )
    result.essay_id = essay_id
    return result


@router.post("/grade/dispute", response_model=DisputeTurnResponse)
async def dispute_turn(
    request: DisputeTurnRequest,
    teacher: TeacherIdentity = Depends(get_current_teacher),
    client: GradingModelClient = Depends(get_grading_client),
    database: Database = Depends(get_database),
) -> DisputeTurnResponse:
    anthropic_messages = [
        {"role": "user" if m.role == "teacher" else "assistant", "content": m.content}
        for m in request.messages
    ]

    try:
        result = await run_dispute_turn(
            client, request.essay_text, request.assignment_prompt, request.original, anthropic_messages
        )
    except GradingModelError as exc:
        raise HTTPException(
            status_code=502,
            detail={"error": "dispute_turn_failed", "message": str(exc)},
        ) from exc

    try:
        proposal_raw_grade_id = await database.persist_dispute_turn(
            essay_id=request.essay_id,
            caller_teacher_id=teacher.sub,
            criterion_id=request.original.criterion_id,
            teacher_message=request.messages[-1].content,
            assistant_message=result.message,
            proposal=result.proposal,
            model_version=client.model_version,
        )
    except EssayNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "essay_not_found", "message": str(exc)},
        ) from exc
    except EssayAccessDeniedError as exc:
        raise HTTPException(
            status_code=403,
            detail={"error": "essay_access_denied", "message": str(exc)},
        ) from exc

    return DisputeTurnResponse(
        message=result.message, proposal=result.proposal, proposal_raw_grade_id=proposal_raw_grade_id
    )


@router.post("/grade/dispute/resolve", response_model=DisputeResolveResponse)
async def resolve_dispute(
    request: DisputeResolveRequest,
    teacher: TeacherIdentity = Depends(get_current_teacher),
    database: Database = Depends(get_database),
) -> DisputeResolveResponse:
    try:
        accepted_grade_id, score, missing = await database.resolve_dispute(
            essay_id=request.essay_id,
            criterion_id=request.criterion_id,
            resolution=request.resolution,
            raw_grade_id=request.raw_grade_id,
        )
    except DisputeNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "dispute_not_found", "message": str(exc)},
        ) from exc
    except RawGradeMismatchError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "raw_grade_mismatch", "message": str(exc)},
        ) from exc

    return DisputeResolveResponse(accepted_grade_id=accepted_grade_id, score=score, missing=missing)
