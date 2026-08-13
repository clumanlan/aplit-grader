import pytest

from aplit_grader.schemas.rubric import Sentence
from aplit_grader.services.conclusion import run_conclusion_call
from aplit_grader.services.inference import GradingModelError
from tests.fixtures.fake_grading_client import FakeGradingModelClient

ESSAY_TEXT = "In the end, hope cannot outrun the past, no matter how bright the light seems."

ASSIGNMENT_PROMPT = "Analyze how a central symbol develops a theme about hope in the novel."

SENTENCES = [
    Sentence(sentence_index=0, section="conclusion", span_start=0, span_end=len(ESSAY_TEXT), text=ESSAY_TEXT),
]


@pytest.mark.asyncio
async def test_returns_conclusion_criterion_on_happy_path():
    client = FakeGradingModelClient(
        {
            "score": 3,
            "missing": False,
            "strengths": ["Synthesizes both paragraphs' evidence"],
            "critiques": ["Insight stays fairly surface-level"],
            "reasoning": "Held at 3 rather than 4 because the connection is present but not deeply developed.",
            "sentence_refs": [0],
        }
    )

    result = await run_conclusion_call(
        client,
        ESSAY_TEXT,
        SENTENCES,
        extracted_thesis="Hope is doomed.",
        body1_coverage_summary="BP1 covers the green light.",
        body2_coverage_summary="BP2 covers the mansion.",
        assignment_prompt=ASSIGNMENT_PROMPT,
    )

    assert result.criterion_id == "conclusion"
    assert result.score == 3


@pytest.mark.asyncio
async def test_handles_a_missing_conclusion():
    client = FakeGradingModelClient(
        {
            "score": None,
            "missing": True,
            "strengths": [],
            "critiques": ["No concluding synthesis found"],
            "reasoning": "Essay ends mid-argument with no wrap-up.",
            "sentence_refs": [],
        }
    )

    result = await run_conclusion_call(
        client,
        ESSAY_TEXT,
        SENTENCES,
        extracted_thesis="Hope is doomed.",
        body1_coverage_summary="BP1 covers the green light.",
        body2_coverage_summary="BP2 covers the mansion.",
        assignment_prompt=ASSIGNMENT_PROMPT,
    )

    assert result.missing is True
    assert result.score is None


@pytest.mark.asyncio
async def test_raises_on_malformed_tool_output():
    client = FakeGradingModelClient({"score": 3})

    with pytest.raises(GradingModelError):
        await run_conclusion_call(
            client,
            ESSAY_TEXT,
            SENTENCES,
            extracted_thesis="Hope is doomed.",
            body1_coverage_summary="BP1 covers the green light.",
            body2_coverage_summary="BP2 covers the mansion.",
            assignment_prompt=ASSIGNMENT_PROMPT,
        )


@pytest.mark.asyncio
async def test_prompt_includes_thesis_both_coverage_summaries_and_rubric_text():
    client = FakeGradingModelClient(
        {
            "score": 3,
            "missing": False,
            "strengths": [],
            "critiques": [],
            "reasoning": "...",
            "sentence_refs": [0],
        }
    )

    await run_conclusion_call(
        client,
        ESSAY_TEXT,
        SENTENCES,
        extracted_thesis="Hope is doomed.",
        body1_coverage_summary="BP1 covers the green light.",
        body2_coverage_summary="BP2 covers the mansion.",
        assignment_prompt=ASSIGNMENT_PROMPT,
    )

    user_prompt = client.calls[0]["user_prompt"]
    assert "Hope is doomed." in user_prompt
    assert "BP1 covers the green light." in user_prompt
    assert "BP2 covers the mansion." in user_prompt
    assert "Connections are made between all paragraphs" in user_prompt
    assert ASSIGNMENT_PROMPT in user_prompt
