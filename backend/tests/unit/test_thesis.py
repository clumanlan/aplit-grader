import pytest

from aplit_grader.schemas.rubric import Sentence
from aplit_grader.services.inference import GradingModelError
from aplit_grader.services.thesis import run_thesis_call
from tests.fixtures.fake_grading_client import FakeGradingModelClient

ESSAY_TEXT = "The green light shows Gatsby's hope is doomed. Gatsby buys a mansion across the bay."

ASSIGNMENT_PROMPT = "Analyze how a central symbol develops a theme about hope in the novel."

SENTENCES = [
    Sentence(sentence_index=0, section="thesis", span_start=0, span_end=48, text=ESSAY_TEXT[0:48]),
    Sentence(sentence_index=1, section="body_1", span_start=49, span_end=88, text=ESSAY_TEXT[49:88]),
]


@pytest.mark.asyncio
async def test_returns_thesis_criterion_and_extracted_thesis_on_happy_path():
    client = FakeGradingModelClient(
        {
            "score": 3,
            "missing": False,
            "strengths": ["Clear, arguable claim"],
            "critiques": ["Could be more concise"],
            "reasoning": "Held at 3 rather than 4 because it's accurate but slightly wordy.",
            "sentence_refs": [0],
            "confidence_level": "high",
            "confidence_reason": "explicit thesis stated",
            "extracted_thesis": "The green light symbolizes Gatsby's doomed hope.",
        }
    )

    result = await run_thesis_call(client, ESSAY_TEXT, SENTENCES, ASSIGNMENT_PROMPT)

    assert result.criterion.criterion_id == "thesis"
    assert result.criterion.score == 3
    assert result.criterion.confidence_level == "high"
    assert result.extracted_thesis == "The green light symbolizes Gatsby's doomed hope."


@pytest.mark.asyncio
async def test_reconstructed_thesis_is_still_returned_when_thesis_is_missing():
    client = FakeGradingModelClient(
        {
            "score": None,
            "missing": True,
            "strengths": [],
            "critiques": ["No explicit thesis statement found"],
            "reasoning": "No sentence states an arguable claim.",
            "sentence_refs": [],
            "confidence_level": "low",
            "confidence_reason": "not found anywhere in the essay",
            "extracted_thesis": "Reconstructed: the essay implies hope cannot survive contact with reality.",
        }
    )

    result = await run_thesis_call(client, ESSAY_TEXT, SENTENCES, ASSIGNMENT_PROMPT)

    assert result.criterion.missing is True
    assert result.criterion.score is None
    assert result.extracted_thesis.startswith("Reconstructed:")


@pytest.mark.asyncio
async def test_raises_on_malformed_tool_output():
    client = FakeGradingModelClient({"score": 3})

    with pytest.raises(GradingModelError):
        await run_thesis_call(client, ESSAY_TEXT, SENTENCES, ASSIGNMENT_PROMPT)


@pytest.mark.asyncio
async def test_prompt_includes_thesis_rubric_text_and_thesis_sentences():
    client = FakeGradingModelClient(
        {
            "score": 3,
            "missing": False,
            "strengths": [],
            "critiques": [],
            "reasoning": "...",
            "sentence_refs": [0],
            "confidence_level": "high",
            "confidence_reason": "explicit thesis stated",
            "extracted_thesis": "...",
        }
    )

    await run_thesis_call(client, ESSAY_TEXT, SENTENCES, ASSIGNMENT_PROMPT)

    user_prompt = client.calls[0]["user_prompt"]
    assert "Shows you thought deeply about the question AND text" in user_prompt
    assert "The green light shows Gatsby's hope is doomed" in user_prompt
    assert ASSIGNMENT_PROMPT in user_prompt
