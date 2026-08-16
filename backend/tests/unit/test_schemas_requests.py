import pytest
from pydantic import ValidationError

from aplit_grader.schemas.requests import GradeRequest, GradeResponse
from aplit_grader.schemas.rubric import CriterionResult, Sentence
from aplit_grader.services.rubric import RUBRIC


def _valid_criterion_results() -> list[CriterionResult]:
    return [
        CriterionResult(
            criterion_id=criterion_id,
            score=3,
            missing=False,
            strengths=[],
            critiques=[],
            reasoning="Stub reasoning.",
            sentence_refs=[],
        )
        for criterion_id in RUBRIC
    ]


def test_grade_request_accepts_essay_text_prompt_and_optional_student_name():
    request = GradeRequest(
        essay_text="Once upon a time...",
        assignment_prompt="Analyze how the author develops a theme.",
        class_id="Period 3 — AP Lit",
        student_name="Jane Doe",
    )

    assert request.essay_text == "Once upon a time..."
    assert request.assignment_prompt == "Analyze how the author develops a theme."
    assert request.class_id == "Period 3 — AP Lit"
    assert request.student_name == "Jane Doe"


def test_grade_request_allows_omitted_student_name():
    request = GradeRequest(
        essay_text="Once upon a time...",
        assignment_prompt="Analyze how the author develops a theme.",
        class_id="Period 3 — AP Lit",
    )

    assert request.student_name is None


def test_grade_request_rejects_empty_essay_text():
    with pytest.raises(ValidationError):
        GradeRequest(
            essay_text="",
            assignment_prompt="Analyze how the author develops a theme.",
            class_id="Period 3 — AP Lit",
        )


def test_grade_request_rejects_empty_assignment_prompt():
    with pytest.raises(ValidationError):
        GradeRequest(
            essay_text="Once upon a time...", assignment_prompt="", class_id="Period 3 — AP Lit"
        )


def test_grade_request_rejects_empty_class_id():
    with pytest.raises(ValidationError):
        GradeRequest(
            essay_text="Once upon a time...",
            assignment_prompt="Analyze how the author develops a theme.",
            class_id="",
        )


def test_grade_response_accepts_all_fourteen_criteria_and_sentences():
    response = GradeResponse(
        criteria=_valid_criterion_results(),
        sentences=[
            Sentence(sentence_index=0, section="thesis", span_start=0, span_end=10, text="..."),
        ],
        segmentation_notes=None,
    )

    assert len(response.criteria) == 14
    assert response.segmentation_notes is None


def test_grade_response_rejects_a_missing_criterion():
    incomplete = _valid_criterion_results()[:-1]

    with pytest.raises(ValidationError):
        GradeResponse(criteria=incomplete, sentences=[], segmentation_notes=None)


def test_grade_response_rejects_a_duplicate_criterion_id():
    duplicated = _valid_criterion_results()
    duplicated.append(duplicated[0])

    with pytest.raises(ValidationError):
        GradeResponse(criteria=duplicated, sentences=[], segmentation_notes=None)
