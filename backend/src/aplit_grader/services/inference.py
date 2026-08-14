import json
from abc import ABC, abstractmethod
from typing import Any, Protocol

import anthropic


class GradingModelError(Exception):
    """Raised when a grading model call fails to produce the expected structured output."""


class GradingModelClient(ABC):
    @property
    @abstractmethod
    def model_version(self) -> str: ...

    @abstractmethod
    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tool_name: str,
        tool_description: str,
        tool_input_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Call the model with forced tool use and return the tool call's input."""
        ...


def _repair_stringified_fields(raw: dict[str, Any], tool_input_schema: dict[str, Any]) -> dict[str, Any]:
    """Occasionally a tool call comes back with an array/object-typed field double-encoded
    as a JSON string instead of a native value — observed with claude-sonnet-5 on a
    segmentation call: {"sentence_sections": "{\\"sentence_sections\\":[...]}"} instead of
    a native array under that key. The model's underlying answer is correct, just wrapped
    one level too deep. Detect and unwrap this per the tool's declared JSON Schema types,
    rather than blindly parsing every string field — a field that's genuinely plain text
    (e.g. a reasoning string) is left untouched.
    """
    properties = tool_input_schema.get("properties", {})
    repaired = dict(raw)
    for field_name, field_schema in properties.items():
        expected_type = field_schema.get("type")
        if expected_type not in ("array", "object"):
            continue
        value = repaired.get(field_name)
        if not isinstance(value, str):
            continue
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            continue
        if isinstance(decoded, dict) and field_name in decoded:
            decoded = decoded[field_name]
        if (expected_type == "array" and isinstance(decoded, list)) or (
            expected_type == "object" and isinstance(decoded, dict)
        ):
            repaired[field_name] = decoded
    return repaired


class _AnthropicSDKClient(Protocol):
    messages: Any


class AnthropicGradingClient(GradingModelClient):
    def __init__(self, *, model: str, sdk_client: _AnthropicSDKClient | None = None, api_key: str | None = None):
        self._model = model
        self._client = sdk_client if sdk_client is not None else anthropic.AsyncAnthropic(api_key=api_key)

    @property
    def model_version(self) -> str:
        return self._model

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tool_name: str,
        tool_description: str,
        tool_input_schema: dict[str, Any],
    ) -> dict[str, Any]:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            tools=[
                {
                    "name": tool_name,
                    "description": tool_description,
                    "input_schema": tool_input_schema,
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
        )

        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and block.name == tool_name:
                return _repair_stringified_fields(block.input, tool_input_schema)

        raise GradingModelError(f"No tool_use block for '{tool_name}' in model response")
