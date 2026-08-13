from typing import Any

from aplit_grader.services.inference import GradingModelClient


class FakeGradingModelClient(GradingModelClient):
    """Test double for GradingModelClient. Returns canned response(s) and records calls.

    Pass `response` for tests that only make one call (reused for every call).
    Pass `responses` for tests that drive multiple calls in sequence (e.g. the
    pipeline) — each call pops the next item off the queue.
    """

    def __init__(
        self,
        response: dict[str, Any] | None = None,
        responses: list[dict[str, Any]] | None = None,
        model_version: str = "fake-model",
    ):
        if response is None and responses is None:
            raise ValueError("must provide either response or responses")
        self._single_response = response
        self._responses_queue = list(responses) if responses is not None else None
        self._model_version = model_version
        self.calls: list[dict[str, Any]] = []

    @property
    def model_version(self) -> str:
        return self._model_version

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tool_name: str,
        tool_description: str,
        tool_input_schema: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "tool_name": tool_name,
                "tool_description": tool_description,
                "tool_input_schema": tool_input_schema,
            }
        )
        if self._responses_queue is not None:
            return self._responses_queue.pop(0)
        return self._single_response
