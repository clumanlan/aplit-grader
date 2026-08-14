from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from aplit_grader.services.inference import AnthropicGradingClient, GradingModelError


def _fake_anthropic_client(tool_input: dict, tool_name: str = "submit_result"):
    response = SimpleNamespace(
        content=[
            SimpleNamespace(type="tool_use", name=tool_name, input=tool_input),
        ]
    )
    fake = SimpleNamespace(messages=SimpleNamespace(create=AsyncMock(return_value=response)))
    return fake


@pytest.mark.asyncio
async def test_generate_structured_returns_the_tool_calls_input():
    fake_client = _fake_anthropic_client({"score": 3}, tool_name="submit_result")
    client = AnthropicGradingClient(model="claude-sonnet-5-test", sdk_client=fake_client)

    result = await client.generate_structured(
        system_prompt="system",
        user_prompt="user",
        tool_name="submit_result",
        tool_description="Submit the result.",
        tool_input_schema={"type": "object", "properties": {"score": {"type": "integer"}}},
    )

    assert result == {"score": 3}


@pytest.mark.asyncio
async def test_generate_structured_raises_when_no_matching_tool_use_block():
    fake_client = _fake_anthropic_client({"score": 3}, tool_name="some_other_tool")
    client = AnthropicGradingClient(model="claude-sonnet-5-test", sdk_client=fake_client)

    with pytest.raises(GradingModelError):
        await client.generate_structured(
            system_prompt="system",
            user_prompt="user",
            tool_name="submit_result",
            tool_description="Submit the result.",
            tool_input_schema={"type": "object"},
        )


@pytest.mark.asyncio
async def test_generate_structured_forces_tool_choice_and_passes_model_version():
    fake_client = _fake_anthropic_client({"score": 3})
    client = AnthropicGradingClient(model="claude-sonnet-5-test", sdk_client=fake_client)

    await client.generate_structured(
        system_prompt="system",
        user_prompt="user",
        tool_name="submit_result",
        tool_description="Submit the result.",
        tool_input_schema={"type": "object"},
    )

    call_kwargs = fake_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-5-test"
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": "submit_result"}


def test_model_version_property_matches_constructor_arg():
    client = AnthropicGradingClient(model="claude-sonnet-5-test", sdk_client=_fake_anthropic_client({}))

    assert client.model_version == "claude-sonnet-5-test"


@pytest.mark.asyncio
async def test_generate_structured_unwraps_an_array_field_double_encoded_as_a_json_string():
    # Observed live: the model wrapped its whole correct answer as a JSON string under
    # the same key, one level too deep, instead of returning a native array.
    stringified = (
        '{"sentence_sections":[{"sentence_index":0,"section":"thesis"},'
        '{"sentence_index":1,"section":"body_1"}]}'
    )
    fake_client = _fake_anthropic_client({"sentence_sections": stringified}, tool_name="submit_segmentation")
    client = AnthropicGradingClient(model="claude-sonnet-5-test", sdk_client=fake_client)

    result = await client.generate_structured(
        system_prompt="system",
        user_prompt="user",
        tool_name="submit_segmentation",
        tool_description="Assign sections.",
        tool_input_schema={
            "type": "object",
            "properties": {"sentence_sections": {"type": "array"}},
        },
    )

    assert result == {
        "sentence_sections": [
            {"sentence_index": 0, "section": "thesis"},
            {"sentence_index": 1, "section": "body_1"},
        ]
    }


@pytest.mark.asyncio
async def test_generate_structured_leaves_a_plain_string_field_untouched():
    fake_client = _fake_anthropic_client(
        {"sentence_sections": [{"sentence_index": 0, "section": "thesis"}], "segmentation_notes": "merged 3 into 2"},
        tool_name="submit_segmentation",
    )
    client = AnthropicGradingClient(model="claude-sonnet-5-test", sdk_client=fake_client)

    result = await client.generate_structured(
        system_prompt="system",
        user_prompt="user",
        tool_name="submit_segmentation",
        tool_description="Assign sections.",
        tool_input_schema={
            "type": "object",
            "properties": {
                "sentence_sections": {"type": "array"},
                "segmentation_notes": {"type": ["string", "null"]},
            },
        },
    )

    assert result["segmentation_notes"] == "merged 3 into 2"


@pytest.mark.asyncio
async def test_generate_structured_leaves_a_field_alone_when_it_isnt_valid_json():
    fake_client = _fake_anthropic_client({"sentence_sections": "not json at all"}, tool_name="submit_segmentation")
    client = AnthropicGradingClient(model="claude-sonnet-5-test", sdk_client=fake_client)

    result = await client.generate_structured(
        system_prompt="system",
        user_prompt="user",
        tool_name="submit_segmentation",
        tool_description="Assign sections.",
        tool_input_schema={
            "type": "object",
            "properties": {"sentence_sections": {"type": "array"}},
        },
    )

    assert result["sentence_sections"] == "not json at all"
