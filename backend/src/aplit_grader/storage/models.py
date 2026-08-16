"""SQLAlchemy ORM models mirroring /schema.sql exactly. See that file's comments for
the full rationale behind each column/constraint — not duplicated here.
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class GradingSession(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    teacher_id: Mapped[str] = mapped_column(nullable=False)
    criteria_selection: Mapped[dict] = mapped_column(JSONB, nullable=False)
    assignment_prompt: Mapped[str] = mapped_column(nullable=False)
    class_id: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Essay(Base):
    __tablename__ = "essays"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    teacher_id: Mapped[str] = mapped_column(nullable=False)
    student_name: Mapped[str | None] = mapped_column(nullable=True)
    essay_text: Mapped[str] = mapped_column(nullable=False)
    segmentation_notes: Mapped[str | None] = mapped_column(nullable=True)
    s3_key: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class RawGrade(Base):
    __tablename__ = "raw_grades"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    essay_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("essays.id"), nullable=False)
    criterion_id: Mapped[str] = mapped_column(nullable=False)
    score: Mapped[int | None] = mapped_column(nullable=True)
    missing: Mapped[bool] = mapped_column(nullable=False)
    strengths: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    critiques: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    reasoning: Mapped[str] = mapped_column(nullable=False)
    sentence_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    confidence_level: Mapped[str | None] = mapped_column(nullable=True)
    confidence_reason: Mapped[str | None] = mapped_column(nullable=True)
    source: Mapped[str] = mapped_column(nullable=False)
    # The grading run that produced this row — matches the S3 key's {run_id} segment
    # (storage/result_logger.py). Nullable: existing rows predate this column, and a
    # dispute-proposal row's run_id is looked up from an existing sibling row rather
    # than being independently generated (a dispute thread has no run of its own).
    run_id: Mapped[str | None] = mapped_column(nullable=True)
    model_version: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AcceptedGrade(Base):
    __tablename__ = "accepted_grades"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    essay_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("essays.id"), nullable=False)
    criterion_id: Mapped[str] = mapped_column(nullable=False)
    score: Mapped[int | None] = mapped_column(nullable=True)
    missing: Mapped[bool] = mapped_column(nullable=False)
    raw_grade_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("raw_grades.id"), nullable=False)
    accepted_via: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Dispute(Base):
    __tablename__ = "disputes"
    __table_args__ = (
        UniqueConstraint(
            "essay_id", "criterion_id", "status", name="one_open_dispute_per_criterion"
        ),
        CheckConstraint("status IN ('open', 'resolved')", name="disputes_status_check"),
        CheckConstraint(
            "resolution IN ('corrected', 'kept_original')", name="disputes_resolution_check"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    essay_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("essays.id"), nullable=False)
    teacher_id: Mapped[str] = mapped_column(nullable=False)
    class_id: Mapped[str | None] = mapped_column(nullable=True)
    criterion_id: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, default="open")
    opened_at: Mapped[datetime] = mapped_column(server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    resolution: Mapped[str | None] = mapped_column(nullable=True)
    accepted_grade_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accepted_grades.id"), nullable=True
    )


class DisputeMessageRow(Base):
    __tablename__ = "dispute_messages"
    __table_args__ = (
        CheckConstraint("role IN ('teacher', 'claude')", name="dispute_messages_role_check"),
        CheckConstraint(
            "proposed_score IS NULL OR raw_grade_id IS NOT NULL", name="dispute_messages_check"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    dispute_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("disputes.id"), nullable=False)
    role: Mapped[str] = mapped_column(nullable=False)
    message_text: Mapped[str] = mapped_column(nullable=False)
    proposed_score: Mapped[int | None] = mapped_column(nullable=True)
    raw_grade_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("raw_grades.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
