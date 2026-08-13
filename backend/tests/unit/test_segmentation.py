import pytest

from aplit_grader.services.inference import GradingModelError
from aplit_grader.services.segmentation import run_segmentation_call
from tests.fixtures.fake_grading_client import FakeGradingModelClient

ESSAY_TEXT = (
    "The green light shows Gatsby's hope is doomed. "
    "Gatsby buys a mansion across the bay. "
    "The mansion fails to win Daisy back. "
    "Ultimately, hope cannot outrun the past."
)


@pytest.mark.asyncio
async def test_assigns_model_sections_onto_deterministically_split_sentences():
    client = FakeGradingModelClient(
        {
            "sentence_sections": [
                {"sentence_index": 0, "section": "thesis"},
                {"sentence_index": 1, "section": "body_1"},
                {"sentence_index": 2, "section": "body_1"},
                {"sentence_index": 3, "section": "conclusion"},
            ],
            "segmentation_notes": None,
        }
    )

    result = await run_segmentation_call(client, ESSAY_TEXT)

    assert [s.section for s in result.sentences] == ["thesis", "body_1", "body_1", "conclusion"]
    assert result.segmentation_notes is None
    # Offsets/text still come from the deterministic splitter, not the model.
    for sentence in result.sentences:
        assert ESSAY_TEXT[sentence.span_start : sentence.span_end] == sentence.text


@pytest.mark.asyncio
async def test_forwards_segmentation_notes_when_a_judgment_call_was_made():
    client = FakeGradingModelClient(
        {
            "sentence_sections": [
                {"sentence_index": 0, "section": "thesis"},
                {"sentence_index": 1, "section": "body_1"},
                {"sentence_index": 2, "section": "body_2"},
                {"sentence_index": 3, "section": "conclusion"},
            ],
            "segmentation_notes": (
                "Essay only had 3 body sentences with no clean paragraph break; "
                "split sentences 1 and 2 into body_1/body_2 by content shift."
            ),
        }
    )

    result = await run_segmentation_call(client, ESSAY_TEXT)

    assert "no clean paragraph break" in result.segmentation_notes


@pytest.mark.asyncio
async def test_raises_when_a_sentence_is_left_unassigned():
    client = FakeGradingModelClient(
        {
            "sentence_sections": [
                {"sentence_index": 0, "section": "thesis"},
                {"sentence_index": 1, "section": "body_1"},
                {"sentence_index": 2, "section": "body_2"},
                # sentence_index 3 missing
            ],
            "segmentation_notes": None,
        }
    )

    with pytest.raises(GradingModelError):
        await run_segmentation_call(client, ESSAY_TEXT)


@pytest.mark.asyncio
async def test_raises_on_malformed_tool_output():
    client = FakeGradingModelClient({"unexpected_shape": True})

    with pytest.raises(GradingModelError):
        await run_segmentation_call(client, ESSAY_TEXT)
