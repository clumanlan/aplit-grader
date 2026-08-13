import pytest

from aplit_grader.schemas.rubric import Sentence
from aplit_grader.services.body_paragraph import run_body_paragraph_call
from aplit_grader.services.inference import GradingModelError
from aplit_grader.services.rubric import criteria_for_section
from tests.fixtures.fake_grading_client import FakeGradingModelClient

ESSAY_TEXT = "Body paragraph one text goes here for grading purposes."

ASSIGNMENT_PROMPT = "Analyze how a central symbol develops a theme about hope in the novel."

SENTENCES = [
    Sentence(sentence_index=0, section="body_1", span_start=0, span_end=len(ESSAY_TEXT), text=ESSAY_TEXT),
]


def _canned_criteria(section: str) -> list[dict]:
    return [
        {
            "criterion_id": criterion_id,
            "score": 3,
            "missing": False,
            "strengths": ["Good detail"],
            "critiques": ["Could go deeper"],
            "reasoning": "Held at 3.",
            "sentence_refs": [0],
        }
        for criterion_id in criteria_for_section(section)
    ]


@pytest.mark.asyncio
async def test_body_1_returns_six_bp1_criteria_and_a_coverage_summary():
    client = FakeGradingModelClient(
        {
            "criteria": _canned_criteria("body_1"),
            "coverage_summary": "BP1 argues the green light represents doomed hope, using the closing-paragraph quote.",
        }
    )

    result = await run_body_paragraph_call(
        client,
        ESSAY_TEXT,
        SENTENCES,
        paragraph_num=1,
        extracted_thesis="Hope is doomed.",
        assignment_prompt=ASSIGNMENT_PROMPT,
    )

    assert {c.criterion_id for c in result.criteria} == set(criteria_for_section("body_1"))
    assert result.coverage_summary.startswith("BP1 argues")


@pytest.mark.asyncio
async def test_body_2_returns_six_bp2_criteria_and_uses_prior_coverage_summary_in_prompt():
    client = FakeGradingModelClient(
        {
            "criteria": _canned_criteria("body_2"),
            "coverage_summary": "BP2 covers Gatsby's mansion as a separate symbol from BP1's green light.",
        }
    )

    result = await run_body_paragraph_call(
        client,
        ESSAY_TEXT,
        SENTENCES,
        paragraph_num=2,
        extracted_thesis="Hope is doomed.",
        assignment_prompt=ASSIGNMENT_PROMPT,
        prior_coverage_summary="BP1 argues the green light represents doomed hope.",
    )

    assert {c.criterion_id for c in result.criteria} == set(criteria_for_section("body_2"))
    call = client.calls[0]
    assert "BP1 argues the green light represents doomed hope." in call["user_prompt"]
    assert "redundan" in call["system_prompt"].lower() or "complete" in call["system_prompt"].lower()


@pytest.mark.asyncio
async def test_raises_when_returned_criteria_dont_match_expected_paragraph():
    client = FakeGradingModelClient(
        {
            # Wrong section's criteria returned for a paragraph_num=1 call.
            "criteria": _canned_criteria("body_2"),
            "coverage_summary": "...",
        }
    )

    with pytest.raises(GradingModelError):
        await run_body_paragraph_call(
            client,
            ESSAY_TEXT,
            SENTENCES,
            paragraph_num=1,
            extracted_thesis="Hope is doomed.",
            assignment_prompt=ASSIGNMENT_PROMPT,
        )


@pytest.mark.asyncio
async def test_raises_on_malformed_tool_output():
    client = FakeGradingModelClient({"criteria": "not-a-list"})

    with pytest.raises(GradingModelError):
        await run_body_paragraph_call(
            client,
            ESSAY_TEXT,
            SENTENCES,
            paragraph_num=1,
            extracted_thesis="Hope is doomed.",
            assignment_prompt=ASSIGNMENT_PROMPT,
        )


@pytest.mark.asyncio
async def test_prompt_includes_extracted_thesis_and_rubric_text():
    client = FakeGradingModelClient(
        {"criteria": _canned_criteria("body_1"), "coverage_summary": "..."}
    )

    await run_body_paragraph_call(
        client,
        ESSAY_TEXT,
        SENTENCES,
        paragraph_num=1,
        extracted_thesis="Hope is doomed.",
        assignment_prompt=ASSIGNMENT_PROMPT,
    )

    user_prompt = client.calls[0]["user_prompt"]
    assert "Hope is doomed." in user_prompt
    assert "the direct quote fully supports your claim" in user_prompt
    assert ASSIGNMENT_PROMPT in user_prompt
