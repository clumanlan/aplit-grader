from typing import Literal

from pydantic import BaseModel, Field, computed_field, model_validator

from aplit_grader.services.rubric import RUBRIC, CriterionId

ConfidenceLevel = Literal["high", "medium", "low"]


class CriterionResult(BaseModel):
    criterion_id: CriterionId
    score: int | None = Field(default=None, ge=1, le=4)
    missing: bool
    strengths: list[str]
    critiques: list[str]
    reasoning: str
    sentence_refs: list[int]
    confidence_level: ConfidenceLevel | None = None
    confidence_reason: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def label(self) -> str:
        return RUBRIC[self.criterion_id].label

    @computed_field  # type: ignore[prop-decorator]
    @property
    def group(self) -> str | None:
        # Presentation-only mapping for this response shape: thesis/conclusion
        # render standalone (no group header) in the frontend, matching
        # CriterionCard/RubricKey's existing null-means-standalone convention.
        # RUBRIC itself keeps "Thesis"/"Conclusion" as real Group values (used
        # elsewhere, e.g. get_rubric_text) — this mapping is local to API
        # serialization, not a rubric-definition change.
        raw_group = RUBRIC[self.criterion_id].group
        if raw_group in ("Thesis", "Conclusion"):
            return None
        return raw_group

    @model_validator(mode="after")
    def _score_and_missing_must_be_consistent(self) -> "CriterionResult":
        if self.missing and self.score is not None:
            raise ValueError("score must be null when missing is true")
        if not self.missing and self.score is None:
            raise ValueError("score is required when missing is false")
        return self

    @model_validator(mode="after")
    def _confidence_fields_are_thesis_only(self) -> "CriterionResult":
        has_confidence = self.confidence_level is not None or self.confidence_reason is not None
        if has_confidence and self.criterion_id != "thesis":
            raise ValueError("confidence_level/confidence_reason are only valid on the thesis criterion")
        return self


EssaySection = Literal["thesis", "body_1", "body_2", "conclusion"]


class Sentence(BaseModel):
    sentence_index: int = Field(ge=0)
    section: EssaySection
    span_start: int = Field(ge=0)
    span_end: int
    text: str

    @model_validator(mode="after")
    def _span_end_after_span_start(self) -> "Sentence":
        if self.span_end <= self.span_start:
            raise ValueError("span_end must be greater than span_start")
        return self
