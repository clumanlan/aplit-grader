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
                return block.input

        raise GradingModelError(f"No tool_use block for '{tool_name}' in model response")
