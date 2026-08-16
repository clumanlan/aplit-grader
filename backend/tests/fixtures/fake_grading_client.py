from typing import Any

from aplit_grader.services.inference import ChatTurnResult, GradingModelClient


class FakeGradingModelClient(GradingModelClient):
    """Test double for GradingModelClient. Returns canned response(s) and records calls.

    Pass `response` for tests that only make one call (reused for every call).
    Pass `responses` for tests that drive multiple calls in sequence (e.g. the
    pipeline) — each call pops the next item off the queue.

    `chat_response`/`chat_responses` are the equivalent pair for `generate_chat_turn`,
    each item a `{"text": str, "tool_input": dict | None}` dict.
    """

    def __init__(
        self,
        response: dict[str, Any] | None = None,
        responses: list[dict[str, Any]] | None = None,
        chat_response: dict[str, Any] | None = None,
        chat_responses: list[dict[str, Any]] | None = None,
        model_version: str = "fake-model",
    ):
        if response is None and responses is None and chat_response is None and chat_responses is None:
            raise ValueError("must provide one of response/responses/chat_response/chat_responses")
        self._single_response = response
        self._responses_queue = list(responses) if responses is not None else None
        self._single_chat_response = chat_response
        self._chat_responses_queue = list(chat_responses) if chat_responses is not None else None
        self._model_version = model_version
        self.calls: list[dict[str, Any]] = []
        self.chat_calls: list[dict[str, Any]] = []

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

    async def generate_chat_turn(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, str]],
        tool_name: str,
        tool_description: str,
        tool_input_schema: dict[str, Any],
    ) -> ChatTurnResult:
        self.chat_calls.append(
            {
                "system_prompt": system_prompt,
                "messages": messages,
                "tool_name": tool_name,
                "tool_description": tool_description,
                "tool_input_schema": tool_input_schema,
            }
        )
        if self._chat_responses_queue is not None:
            raw = self._chat_responses_queue.pop(0)
        else:
            raw = self._single_chat_response
        return ChatTurnResult(text=raw["text"], tool_input=raw.get("tool_input"))
