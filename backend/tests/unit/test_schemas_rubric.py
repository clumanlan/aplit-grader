import pytest
from pydantic import ValidationError

from aplit_grader.schemas.rubric import CriterionResult, Sentence


def test_criterion_result_accepts_a_valid_scored_instance():
    result = CriterionResult(
        criterion_id="bp1-evidence-1",
        score=3,
        missing=False,
        strengths=["Uses a direct quote"],
        critiques=["Could use more context"],
        reasoning="Held at 3 rather than 4 because context is thin.",
        sentence_refs=[4, 5],
    )

    assert result.criterion_id == "bp1-evidence-1"
    assert result.score == 3
    assert result.missing is False
    assert result.strengths == ["Uses a direct quote"]
    assert result.critiques == ["Could use more context"]
    assert result.sentence_refs == [4, 5]


def test_criterion_result_accepts_a_valid_missing_instance():
    result = CriterionResult(
        criterion_id="bp1-reasoning-1",
        score=None,
        missing=True,
        strengths=[],
        critiques=["Nothing to point to yet"],
        reasoning="No sentences addressed this criterion.",
        sentence_refs=[],
    )

    assert result.missing is True
    assert result.score is None


def test_criterion_result_rejects_missing_true_with_a_score_set():
    with pytest.raises(ValidationError):
        CriterionResult(
            criterion_id="bp1-reasoning-1",
            score=2,
            missing=True,
            strengths=[],
            critiques=[],
            reasoning="Inconsistent state.",
            sentence_refs=[],
        )


def test_criterion_result_rejects_missing_false_with_no_score():
    with pytest.raises(ValidationError):
        CriterionResult(
            criterion_id="bp1-reasoning-1",
            score=None,
            missing=False,
            strengths=[],
            critiques=[],
            reasoning="Inconsistent state.",
            sentence_refs=[],
        )


@pytest.mark.parametrize("out_of_range_score", [0, 5, -1])
def test_criterion_result_rejects_score_outside_one_to_four(out_of_range_score):
    with pytest.raises(ValidationError):
        CriterionResult(
            criterion_id="bp1-reasoning-1",
            score=out_of_range_score,
            missing=False,
            strengths=[],
            critiques=[],
            reasoning="Out of range.",
            sentence_refs=[],
        )


def test_criterion_result_rejects_an_unknown_criterion_id():
    with pytest.raises(ValidationError):
        CriterionResult(
            criterion_id="not-a-real-criterion",
            score=3,
            missing=False,
            strengths=[],
            critiques=[],
            reasoning="Unknown id.",
            sentence_refs=[],
        )


def test_confidence_fields_default_to_none():
    result = CriterionResult(
        criterion_id="bp1-reasoning-1",
        score=3,
        missing=False,
        strengths=[],
        critiques=[],
        reasoning="No confidence bucket for non-thesis criteria.",
        sentence_refs=[],
    )

    assert result.confidence_level is None
    assert result.confidence_reason is None


def test_thesis_criterion_accepts_confidence_fields():
    result = CriterionResult(
        criterion_id="thesis",
        score=3,
        missing=False,
        strengths=[],
        critiques=[],
        reasoning="Explicit thesis found in the introduction.",
        sentence_refs=[0],
        confidence_level="high",
        confidence_reason="explicit-thesis-present",
    )

    assert result.confidence_level == "high"
    assert result.confidence_reason == "explicit-thesis-present"


def test_non_thesis_criterion_rejects_confidence_fields_being_set():
    with pytest.raises(ValidationError):
        CriterionResult(
            criterion_id="bp1-reasoning-1",
            score=3,
            missing=False,
            strengths=[],
            critiques=[],
            reasoning="Confidence doesn't belong here.",
            sentence_refs=[],
            confidence_level="high",
            confidence_reason="explicit-thesis-present",
        )


def test_sentence_accepts_a_valid_instance():
    sentence = Sentence(
        sentence_index=3,
        section="body_1",
        span_start=100,
        span_end=142,
        text="This is the sentence text.",
    )

    assert sentence.sentence_index == 3
    assert sentence.section == "body_1"
    assert sentence.span_start == 100
    assert sentence.span_end == 142


def test_sentence_rejects_an_unknown_section():
    with pytest.raises(ValidationError):
        Sentence(
            sentence_index=0,
            section="not-a-real-section",
            span_start=0,
            span_end=10,
            text="...",
        )


def test_sentence_rejects_span_end_not_after_span_start():
    with pytest.raises(ValidationError):
        Sentence(
            sentence_index=0,
            section="thesis",
            span_start=50,
            span_end=50,
            text="...",
        )


def test_sentence_rejects_negative_sentence_index():
    with pytest.raises(ValidationError):
        Sentence(
            sentence_index=-1,
            section="thesis",
            span_start=0,
            span_end=10,
            text="...",
        )
