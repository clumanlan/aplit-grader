from pydantic import BaseModel, Field, model_validator

from aplit_grader.schemas.rubric import CriterionResult, Sentence
from aplit_grader.services.rubric import RUBRIC


class GradeRequest(BaseModel):
    essay_text: str = Field(min_length=1)
    assignment_prompt: str = Field(min_length=1)
    student_name: str | None = None


class GradeResponse(BaseModel):
    criteria: list[CriterionResult]
    sentences: list[Sentence]
    segmentation_notes: str | None

    @model_validator(mode="after")
    def _criteria_cover_the_full_rubric_exactly_once(self) -> "GradeResponse":
        ids = [criterion.criterion_id for criterion in self.criteria]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate criterion_id in criteria")
        if set(ids) != set(RUBRIC):
            raise ValueError("criteria must cover exactly the 14 rubric criteria")
        return self
