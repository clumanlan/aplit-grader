import uuid
from typing import Literal

from pydantic import BaseModel, Field, computed_field, model_validator

from aplit_grader.schemas.rubric import CriterionResult, Sentence
from aplit_grader.services.rubric import RUBRIC, CriterionId


class GradeRequest(BaseModel):
    essay_text: str = Field(min_length=1)
    assignment_prompt: str = Field(min_length=1)
    class_id: str = Field(min_length=1)
    student_name: str | None = None


# Backend's internal section naming (Sentence.section, schemas/rubric.py's
# EssaySection Literal) uses "body_1"/"body_2"; the frontend's SectionId type
# uses "bp1"/"bp2". Convert here so the frontend never has to know the
# backend's internal naming.
_SECTION_ID_MAP: dict[str, str] = {
    "thesis": "thesis",
    "body_1": "bp1",
    "body_2": "bp2",
    "conclusion": "conclusion",
}


class GradeResponse(BaseModel):
    # Optional: run_grading_pipeline() constructs this without knowing essay_id (a
    # persistence-layer concept it doesn't need) — routes.py sets it by attribute
    # assignment once POST /grade has actually persisted the essay. Also used
    # unset by services/eval.py's offline zero-shot eval tool and report.py's
    # HTML report renderer, neither of which is backed by a real database row.
    essay_id: uuid.UUID | None = None
    criteria: list[CriterionResult]
    sentences: list[Sentence]
    segmentation_notes: str | None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def section_of(self) -> dict[int, str]:
        return {s.sentence_index: _SECTION_ID_MAP[s.section] for s in self.sentences}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def citing_criteria(self) -> dict[int, list[str]]:
        # Inverts each criterion's sentence_refs into sentence-index -> criterion
        # ids. Same shape as services/report.py's _sentence_criterion_map (which
        # does this today for an internal-only HTML report), reimplemented here
        # to emit ids rather than full CriterionResult objects.
        mapping: dict[int, list[str]] = {}
        for criterion in self.criteria:
            for sentence_index in criterion.sentence_refs:
                mapping.setdefault(sentence_index, []).append(criterion.criterion_id)
        return mapping

    @model_validator(mode="after")
    def _criteria_cover_the_full_rubric_exactly_once(self) -> "GradeResponse":
        ids = [criterion.criterion_id for criterion in self.criteria]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate criterion_id in criteria")
        if set(ids) != set(RUBRIC):
            raise ValueError("criteria must cover exactly the 14 rubric criteria")
        return self


class DisputeMessage(BaseModel):
    role: Literal["teacher", "assistant"]
    content: str = Field(min_length=1)


class DisputeTurnRequest(BaseModel):
    # teacher_id/class_id are deliberately NOT request fields — the server derives
    # both from essay_id (via the essay/session it belongs to) rather than trusting
    # client-supplied values, and rejects the request if the authenticated caller
    # doesn't own that essay. See storage/db.py's persist_dispute_turn.
    essay_id: uuid.UUID
    essay_text: str = Field(min_length=1)
    assignment_prompt: str = Field(min_length=1)
    original: CriterionResult
    messages: list[DisputeMessage] = Field(min_length=1)

    @model_validator(mode="after")
    def _last_message_is_from_the_teacher(self) -> "DisputeTurnRequest":
        if self.messages[-1].role != "teacher":
            raise ValueError("the last message in the transcript must be from the teacher")
        return self


class DisputeTurnResponse(BaseModel):
    message: str
    proposal: CriterionResult | None = None
    # Set only alongside `proposal` — the raw_grades row it was persisted as, so a
    # later "Save correction" can reference it without the server needing to guess
    # which proposal she meant.
    proposal_raw_grade_id: uuid.UUID | None = None


class DisputeResolveRequest(BaseModel):
    essay_id: uuid.UUID
    criterion_id: CriterionId
    resolution: Literal["corrected", "kept_original"]
    # Required (and only meaningful) when resolution == "corrected" — the
    # proposal_raw_grade_id a prior DisputeTurnResponse returned. "kept_original"
    # doesn't need one: the server looks up the essay's original raw_grades row
    # for this criterion itself, since the client was never given that id.
    raw_grade_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _corrected_requires_a_raw_grade_id(self) -> "DisputeResolveRequest":
        if self.resolution == "corrected" and self.raw_grade_id is None:
            raise ValueError("raw_grade_id is required when resolution is 'corrected'")
        return self


class DisputeResolveResponse(BaseModel):
    accepted_grade_id: uuid.UUID
    score: int | None
    missing: bool
