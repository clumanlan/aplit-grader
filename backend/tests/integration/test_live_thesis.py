import os

import pytest

from aplit_grader.schemas.rubric import Sentence
from aplit_grader.services.inference import AnthropicGradingClient
from aplit_grader.services.thesis import run_thesis_call

pytestmark = pytest.mark.live

ESSAY_TEXT = (
    "In The Great Gatsby, Fitzgerald uses the green light to show that Gatsby's hope for "
    "reuniting with Daisy is ultimately unattainable. Gatsby stares across the bay at the "
    "light every night, believing it represents a future he can still reach. By the novel's "
    "end, the light's meaning has shifted from promise to illusion, revealing that some "
    "dreams are shaped more by longing than by reality."
)

ASSIGNMENT_PROMPT = (
    "Analyze how Fitzgerald uses a central symbol to develop a theme about hope and the "
    "past in The Great Gatsby."
)


@pytest.mark.asyncio
async def test_thesis_tool_schema_produces_a_valid_result_against_the_real_api():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    client = AnthropicGradingClient(model="claude-sonnet-5")
    sentences = [
        Sentence(sentence_index=0, section="thesis", span_start=0, span_end=len(ESSAY_TEXT), text=ESSAY_TEXT)
    ]

    result = await run_thesis_call(client, ESSAY_TEXT, sentences, ASSIGNMENT_PROMPT)

    assert result.criterion.criterion_id == "thesis"
    assert result.criterion.confidence_level in ("high", "medium", "low")
    assert result.extracted_thesis.strip() != ""
