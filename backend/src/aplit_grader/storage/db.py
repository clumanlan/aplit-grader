"""Postgres persistence for grading runs and disputes. Sync SQLAlchemy wrapped in
asyncio.to_thread — same pattern LocalResultLogger/S3ResultLogger already use for
their sync I/O, kept consistent rather than pulling in an async driver.
"""

import asyncio
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Literal

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from aplit_grader.schemas.rubric import CriterionResult
from aplit_grader.services.rubric import CriterionId, criteria_for_section
from aplit_grader.storage.models import (
    AcceptedGrade,
    Dispute,
    DisputeMessageRow,
    Essay,
    GradingSession,
    RawGrade,
)

# Inverse of services/rubric.py's criteria_for_section — which of the 4 grading
# calls produced a given criterion, used as raw_grades.source.
_SOURCE_BY_CRITERION: dict[CriterionId, str] = {
    criterion_id: section
    for section in ("thesis", "body_1", "body_2", "conclusion")
    for criterion_id in criteria_for_section(section)  # type: ignore[arg-type]
}

DisputeResolution = Literal["corrected", "kept_original"]

# The 4 grading-call sources, as opposed to 'dispute-proposal' — used to find "the
# original grade" a 'kept_original' resolution should point accepted_grades at.
_ORIGINAL_GRADE_SOURCES = ("thesis", "body_1", "body_2", "conclusion")


class DisputeNotFoundError(Exception):
    """Raised when resolving a dispute that has no open thread for that essay/criterion,
    or when 'kept_original' can't find an original raw_grades row to point at."""


class RawGradeMismatchError(Exception):
    """Raised when a client-supplied raw_grade_id doesn't belong to the essay/criterion
    it's being resolved against."""


class EssayNotFoundError(Exception):
    """Raised when a dispute turn references an essay_id that doesn't exist."""


class EssayAccessDeniedError(Exception):
    """Raised when the authenticated caller doesn't own the essay a dispute references."""


class Database:
    def __init__(self, database_url: str):
        self._engine = create_engine(database_url, pool_pre_ping=True)
        self._session_factory: sessionmaker[Session] = sessionmaker(bind=self._engine)

    @contextmanager
    def _session(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _get_or_create_session(
        self, db: Session, *, teacher_id: str, class_id: str, assignment_prompt: str
    ) -> GradingSession:
        existing = db.execute(
            select(GradingSession).where(
                GradingSession.teacher_id == teacher_id,
                GradingSession.class_id == class_id,
                GradingSession.assignment_prompt == assignment_prompt,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing

        # criteria_selection isn't sent by the frontend yet (POST /grade always
        # grades all 14 criteria today) — {"full_essay": true} records what
        # actually happened rather than fabricating a per-criterion selection.
        session_row = GradingSession(
            teacher_id=teacher_id,
            class_id=class_id,
            assignment_prompt=assignment_prompt,
            criteria_selection={"full_essay": True},
        )
        db.add(session_row)
        db.flush()
        return session_row

    def _persist_grading_run_sync(
        self,
        *,
        run_id: str,
        teacher_id: str,
        class_id: str,
        assignment_prompt: str,
        student_name: str | None,
        essay_text: str,
        segmentation_notes: str | None,
        s3_key: str | None,
        criteria: list[CriterionResult],
        model_version: str,
    ) -> uuid.UUID:
        with self._session() as db:
            session_row = self._get_or_create_session(
                db, teacher_id=teacher_id, class_id=class_id, assignment_prompt=assignment_prompt
            )
            essay = Essay(
                session_id=session_row.id,
                teacher_id=teacher_id,
                student_name=student_name,
                essay_text=essay_text,
                segmentation_notes=segmentation_notes,
                s3_key=s3_key,
            )
            db.add(essay)
            db.flush()

            for criterion in criteria:
                db.add(
                    RawGrade(
                        essay_id=essay.id,
                        criterion_id=criterion.criterion_id,
                        score=criterion.score,
                        missing=criterion.missing,
                        strengths=criterion.strengths,
                        critiques=criterion.critiques,
                        reasoning=criterion.reasoning,
                        sentence_refs=criterion.sentence_refs,
                        confidence_level=criterion.confidence_level,
                        confidence_reason=criterion.confidence_reason,
                        source=_SOURCE_BY_CRITERION[criterion.criterion_id],
                        run_id=run_id,
                        model_version=model_version,
                    )
                )

            return essay.id

    async def persist_grading_run(
        self,
        *,
        run_id: str,
        teacher_id: str,
        class_id: str,
        assignment_prompt: str,
        student_name: str | None,
        essay_text: str,
        segmentation_notes: str | None,
        s3_key: str | None,
        criteria: list[CriterionResult],
        model_version: str,
    ) -> uuid.UUID:
        return await asyncio.to_thread(
            self._persist_grading_run_sync,
            run_id=run_id,
            teacher_id=teacher_id,
            class_id=class_id,
            assignment_prompt=assignment_prompt,
            student_name=student_name,
            essay_text=essay_text,
            segmentation_notes=segmentation_notes,
            s3_key=s3_key,
            criteria=criteria,
            model_version=model_version,
        )

    def _get_or_create_open_dispute(
        self, db: Session, *, essay_id: uuid.UUID, teacher_id: str, class_id: str | None, criterion_id: str
    ) -> Dispute:
        existing = db.execute(
            select(Dispute).where(
                Dispute.essay_id == essay_id,
                Dispute.criterion_id == criterion_id,
                Dispute.status == "open",
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing

        dispute = Dispute(
            essay_id=essay_id, teacher_id=teacher_id, class_id=class_id, criterion_id=criterion_id
        )
        db.add(dispute)
        db.flush()
        return dispute

    def _persist_dispute_turn_sync(
        self,
        *,
        essay_id: uuid.UUID,
        caller_teacher_id: str,
        criterion_id: str,
        teacher_message: str,
        assistant_message: str,
        proposal: CriterionResult | None,
        model_version: str,
    ) -> uuid.UUID | None:
        with self._session() as db:
            essay = db.get(Essay, essay_id)
            if essay is None:
                raise EssayNotFoundError(f"No essay {essay_id}")
            if essay.teacher_id != caller_teacher_id:
                raise EssayAccessDeniedError(
                    f"Essay {essay_id} does not belong to teacher {caller_teacher_id}"
                )
            session_row = db.get(GradingSession, essay.session_id)

            dispute = self._get_or_create_open_dispute(
                db,
                essay_id=essay_id,
                teacher_id=essay.teacher_id,
                class_id=session_row.class_id if session_row is not None else None,
                criterion_id=criterion_id,
            )
            db.add(DisputeMessageRow(dispute_id=dispute.id, role="teacher", message_text=teacher_message))

            raw_grade_id: uuid.UUID | None = None
            if proposal is not None:
                # The dispute thread has no run of its own — inherit the run_id from
                # any existing raw_grades row for this essay (always present, since
                # persist_grading_run wrote 14 of them before any dispute could exist).
                existing_run_id = db.execute(
                    select(RawGrade.run_id).where(RawGrade.essay_id == essay_id).limit(1)
                ).scalar_one_or_none()

                raw_grade = RawGrade(
                    essay_id=essay_id,
                    criterion_id=criterion_id,
                    score=proposal.score,
                    missing=proposal.missing,
                    strengths=proposal.strengths,
                    critiques=proposal.critiques,
                    reasoning=proposal.reasoning,
                    sentence_refs=proposal.sentence_refs,
                    source="dispute-proposal",
                    run_id=existing_run_id,
                    model_version=model_version,
                )
                db.add(raw_grade)
                db.flush()
                raw_grade_id = raw_grade.id

            db.add(
                DisputeMessageRow(
                    dispute_id=dispute.id,
                    role="claude",
                    message_text=assistant_message,
                    proposed_score=proposal.score if proposal is not None else None,
                    raw_grade_id=raw_grade_id,
                )
            )

            return raw_grade_id

    async def persist_dispute_turn(
        self,
        *,
        essay_id: uuid.UUID,
        caller_teacher_id: str,
        criterion_id: str,
        teacher_message: str,
        assistant_message: str,
        proposal: CriterionResult | None,
        model_version: str,
    ) -> uuid.UUID | None:
        return await asyncio.to_thread(
            self._persist_dispute_turn_sync,
            essay_id=essay_id,
            caller_teacher_id=caller_teacher_id,
            criterion_id=criterion_id,
            teacher_message=teacher_message,
            assistant_message=assistant_message,
            proposal=proposal,
            model_version=model_version,
        )

    def _resolve_dispute_sync(
        self,
        *,
        essay_id: uuid.UUID,
        caller_teacher_id: str,
        criterion_id: str,
        resolution: DisputeResolution,
        raw_grade_id: uuid.UUID | None,
    ) -> tuple[uuid.UUID, int | None, bool]:
        with self._session() as db:
            essay = db.get(Essay, essay_id)
            if essay is None:
                raise EssayNotFoundError(f"No essay {essay_id}")
            if essay.teacher_id != caller_teacher_id:
                raise EssayAccessDeniedError(
                    f"Essay {essay_id} does not belong to teacher {caller_teacher_id}"
                )

            dispute = db.execute(
                select(Dispute).where(
                    Dispute.essay_id == essay_id,
                    Dispute.criterion_id == criterion_id,
                    Dispute.status == "open",
                )
            ).scalar_one_or_none()
            if dispute is None:
                raise DisputeNotFoundError(
                    f"No open dispute for essay {essay_id}, criterion {criterion_id}"
                )

            if resolution == "corrected":
                if raw_grade_id is None:
                    raise ValueError("raw_grade_id is required when resolution is 'corrected'")
                raw_grade = db.get(RawGrade, raw_grade_id)
                if raw_grade is None or raw_grade.essay_id != essay_id or raw_grade.criterion_id != criterion_id:
                    raise RawGradeMismatchError(
                        f"raw_grade_id {raw_grade_id} does not belong to essay {essay_id}, "
                        f"criterion {criterion_id}"
                    )
            else:  # kept_original — client doesn't have this id, look up the original grade
                raw_grade = (
                    db.execute(
                        select(RawGrade)
                        .where(
                            RawGrade.essay_id == essay_id,
                            RawGrade.criterion_id == criterion_id,
                            RawGrade.source.in_(_ORIGINAL_GRADE_SOURCES),
                        )
                        .order_by(RawGrade.created_at)
                    )
                    .scalars()
                    .first()
                )
                if raw_grade is None:
                    raise DisputeNotFoundError(
                        f"No original raw_grades row for essay {essay_id}, criterion {criterion_id}"
                    )

            accepted = AcceptedGrade(
                essay_id=essay_id,
                criterion_id=criterion_id,
                score=raw_grade.score,
                missing=raw_grade.missing,
                raw_grade_id=raw_grade.id,
                accepted_via="dispute_save",
            )
            db.add(accepted)
            db.flush()

            dispute.status = "resolved"
            dispute.resolution = resolution
            dispute.accepted_grade_id = accepted.id
            dispute.resolved_at = func.now()

            return accepted.id, raw_grade.score, raw_grade.missing

    async def resolve_dispute(
        self,
        *,
        essay_id: uuid.UUID,
        caller_teacher_id: str,
        criterion_id: str,
        resolution: DisputeResolution,
        raw_grade_id: uuid.UUID | None = None,
    ) -> tuple[uuid.UUID, int | None, bool]:
        return await asyncio.to_thread(
            self._resolve_dispute_sync,
            essay_id=essay_id,
            caller_teacher_id=caller_teacher_id,
            criterion_id=criterion_id,
            resolution=resolution,
            raw_grade_id=raw_grade_id,
        )
