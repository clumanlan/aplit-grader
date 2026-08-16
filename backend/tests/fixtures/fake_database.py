import uuid
from typing import Any


class FakeDatabase:
    """Test double for storage.db.Database — records calls, returns fake ids.
    Keeps the endpoint tests isolated from a real Postgres, same pattern as
    FakeGradingModelClient does for the Anthropic SDK.
    """

    def __init__(self):
        self.grading_run_calls: list[dict[str, Any]] = []
        self.dispute_turn_calls: list[dict[str, Any]] = []
        self.resolve_calls: list[dict[str, Any]] = []
        self.essay_id = uuid.uuid4()
        self.proposal_raw_grade_id = uuid.uuid4()
        self.resolve_response: tuple[uuid.UUID, int | None, bool] = (uuid.uuid4(), 3, False)

    async def persist_grading_run(self, **kwargs: Any) -> uuid.UUID:
        self.grading_run_calls.append(kwargs)
        return self.essay_id

    async def persist_dispute_turn(self, **kwargs: Any) -> uuid.UUID | None:
        self.dispute_turn_calls.append(kwargs)
        return self.proposal_raw_grade_id if kwargs.get("proposal") is not None else None

    async def resolve_dispute(self, **kwargs: Any) -> tuple[uuid.UUID, int | None, bool]:
        self.resolve_calls.append(kwargs)
        return self.resolve_response
