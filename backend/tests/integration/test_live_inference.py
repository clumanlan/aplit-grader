import os

import pytest

from aplit_grader.services.inference import AnthropicGradingClient

pytestmark = pytest.mark.live


@pytest.mark.asyncio
async def test_forced_tool_use_returns_a_well_formed_response():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    client = AnthropicGradingClient(model="claude-sonnet-5")

    result = await client.generate_structured(
        system_prompt="You are a test harness. Always call the tool exactly as instructed.",
        user_prompt="Call the echo_number tool with value set to 42.",
        tool_name="echo_number",
        tool_description="Echo back a number.",
        tool_input_schema={
            "type": "object",
            "properties": {"value": {"type": "integer"}},
            "required": ["value"],
        },
    )

    assert result == {"value": 42}
