import pytest

from aplit_grader.schemas.rubric import CriterionResult
from aplit_grader.services.dispute import run_dispute_turn
from aplit_grader.services.inference import GradingModelError
from tests.fixtures.fake_grading_client import FakeGradingModelClient
from tests.fixtures.sample_essays import (
    GATSBY_ASSIGNMENT_PROMPT,
    GATSBY_FOUR_SENTENCE_ESSAY,
)


def _original_criterion() -> CriterionResult:
    return CriterionResult(
        criterion_id="bp1-evidence-1",
        score=2,
        missing=False,
        strengths=["Quote is relevant."],
        critiques=["Missing context for the quote."],
        reasoning="The evidence is tangential to the claim.",
        sentence_refs=[1],
    )


@pytest.mark.asyncio
async def test_run_dispute_turn_returns_plain_message_when_no_proposal_is_made():
    client = FakeGradingModelClient(
        chat_response={"text": "I'd stand by the 2 — the quote still lacks context.", "tool_input": None}
    )

    result = await run_dispute_turn(
        client,
        GATSBY_FOUR_SENTENCE_ESSAY,
        GATSBY_ASSIGNMENT_PROMPT,
        _original_criterion(),
        [{"role": "user", "content": "I think this deserves a 3."}],
    )

    assert result.message == "I'd stand by the 2 — the quote still lacks context."
    assert result.proposal is None


@pytest.mark.asyncio
async def test_run_dispute_turn_returns_a_proposal_scoped_to_the_original_criterion():
    client = FakeGradingModelClient(
        chat_response={
            "text": "You're right — sentence 2 does supply the missing context. I'd revise this to a 3.",
            "tool_input": {
                "score": 3,
                "missing": False,
                "strengths": ["Quote now has context via sentence 2."],
                "critiques": [],
                "reasoning": "Sentence 2 supplies the context the quote needed.",
                "sentence_refs": [1, 2],
            },
        }
    )

    result = await run_dispute_turn(
        client,
        GATSBY_FOUR_SENTENCE_ESSAY,
        GATSBY_ASSIGNMENT_PROMPT,
        _original_criterion(),
        [{"role": "user", "content": "What about sentence 2? It gives the context."}],
    )

    assert result.proposal is not None
    assert result.proposal.criterion_id == "bp1-evidence-1"
    assert result.proposal.score == 3
    assert result.proposal.sentence_refs == [1, 2]


@pytest.mark.asyncio
async def test_run_dispute_turn_passes_the_full_message_transcript_and_tool_choice_auto():
    client = FakeGradingModelClient(chat_response={"text": "ok", "tool_input": None})
    transcript = [
        {"role": "user", "content": "Why is this a 2?"},
        {"role": "assistant", "content": "The quote lacks context."},
        {"role": "user", "content": "Sentence 2 gives the context though."},
    ]

    await run_dispute_turn(
        client, GATSBY_FOUR_SENTENCE_ESSAY, GATSBY_ASSIGNMENT_PROMPT, _original_criterion(), transcript
    )

    call = client.chat_calls[0]
    assert call["messages"] == transcript
    assert call["tool_name"] == "propose_revised_grade"


@pytest.mark.asyncio
async def test_run_dispute_turn_raises_when_the_proposal_is_malformed():
    client = FakeGradingModelClient(
        chat_response={"text": "here's the revision", "tool_input": {"score": "not-an-int"}}
    )

    with pytest.raises(GradingModelError):
        await run_dispute_turn(
            client,
            GATSBY_FOUR_SENTENCE_ESSAY,
            GATSBY_ASSIGNMENT_PROMPT,
            _original_criterion(),
            [{"role": "user", "content": "revise it"}],
        )


@pytest.mark.asyncio
async def test_run_dispute_turn_raises_when_no_text_and_no_proposal():
    client = FakeGradingModelClient(chat_response={"text": "", "tool_input": None})

    with pytest.raises(GradingModelError):
        await run_dispute_turn(
            client,
            GATSBY_FOUR_SENTENCE_ESSAY,
            GATSBY_ASSIGNMENT_PROMPT,
            _original_criterion(),
            [{"role": "user", "content": "hello?"}],
        )


@pytest.mark.asyncio
async def test_run_dispute_turn_falls_back_to_a_default_message_when_only_a_proposal_is_returned():
    client = FakeGradingModelClient(
        chat_response={
            "text": "",
            "tool_input": {
                "score": 3,
                "missing": False,
                "strengths": [],
                "critiques": [],
                "reasoning": "Revised per new evidence.",
                "sentence_refs": [1],
            },
        }
    )

    result = await run_dispute_turn(
        client,
        GATSBY_FOUR_SENTENCE_ESSAY,
        GATSBY_ASSIGNMENT_PROMPT,
        _original_criterion(),
        [{"role": "user", "content": "revise it"}],
    )

    assert result.message == "Updated the grade to reflect that."
    assert result.proposal is not None
