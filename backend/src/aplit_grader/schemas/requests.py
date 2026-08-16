from pydantic import BaseModel, Field, computed_field, model_validator

from aplit_grader.schemas.rubric import CriterionResult, Sentence
from aplit_grader.services.rubric import RUBRIC


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
