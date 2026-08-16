import uuid

import pytest
from fastapi.testclient import TestClient

from aplit_grader.api.auth import TeacherIdentity, get_current_teacher
from aplit_grader.api.routes import get_database, get_grading_client
from aplit_grader.main import app
from aplit_grader.storage.db import EssayAccessDeniedError, EssayNotFoundError
from tests.fixtures.fake_database import FakeDatabase
from tests.fixtures.fake_grading_client import FakeGradingModelClient
from tests.fixtures.sample_essays import (
    GATSBY_ASSIGNMENT_PROMPT,
    GATSBY_FOUR_SENTENCE_ESSAY,
)

ESSAY_ID = str(uuid.uuid4())

_ORIGINAL_CRITERION = {
    "criterion_id": "bp1-evidence-1",
    "score": 2,
    "missing": False,
    "strengths": ["Quote is relevant."],
    "critiques": ["Missing context for the quote."],
    "reasoning": "The evidence is tangential to the claim.",
    "sentence_refs": [1],
}


class _RaisingDatabase(FakeDatabase):
    def __init__(self, error: Exception):
        super().__init__()
        self._error = error

    async def persist_dispute_turn(self, **kwargs):
        self.dispute_turn_calls.append(kwargs)
        raise self._error


@pytest.fixture
def fake_database():
    return FakeDatabase()


@pytest.fixture
def dispute_client(fake_database):
    def _make(chat_response: dict):
        fake_client = FakeGradingModelClient(chat_response=chat_response)
        app.dependency_overrides[get_grading_client] = lambda: fake_client
        app.dependency_overrides[get_database] = lambda: fake_database
        app.dependency_overrides[get_current_teacher] = lambda: TeacherIdentity(
            sub="test-teacher-sub", username="teacher@example.com"
        )
        return TestClient(app), fake_client

    yield _make
    app.dependency_overrides.clear()


def _base_payload(messages: list[dict]) -> dict:
    return {
        "essay_id": ESSAY_ID,
        "essay_text": GATSBY_FOUR_SENTENCE_ESSAY,
        "assignment_prompt": GATSBY_ASSIGNMENT_PROMPT,
        "original": _ORIGINAL_CRITERION,
        "messages": messages,
    }


def test_dispute_endpoint_returns_a_plain_reply_with_no_proposal(dispute_client):
    client, _ = dispute_client({"text": "I'd stand by the 2.", "tool_input": None})

    response = client.post(
        "/grade/dispute",
        json=_base_payload([{"role": "teacher", "content": "I think this deserves a 3."}]),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "I'd stand by the 2."
    assert body["proposal"] is None
    assert body["proposal_raw_grade_id"] is None


def test_dispute_endpoint_returns_a_proposal_when_the_model_calls_the_tool(dispute_client, fake_database):
    client, _ = dispute_client(
        {
            "text": "Fair point — I'd revise this to a 3.",
            "tool_input": {
                "score": 3,
                "missing": False,
                "strengths": ["Sentence 2 supplies context."],
                "critiques": [],
                "reasoning": "Sentence 2 supplies the missing context.",
                "sentence_refs": [1, 2],
            },
        }
    )

    response = client.post(
        "/grade/dispute",
        json=_base_payload([{"role": "teacher", "content": "Sentence 2 gives the context though."}]),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["proposal"]["criterion_id"] == "bp1-evidence-1"
    assert body["proposal"]["score"] == 3
    assert body["proposal_raw_grade_id"] == str(fake_database.proposal_raw_grade_id)


def test_dispute_endpoint_persists_the_turn_against_the_given_essay_and_criterion(
    dispute_client, fake_database
):
    client, _ = dispute_client({"text": "I'd stand by the 2.", "tool_input": None})

    client.post(
        "/grade/dispute",
        json=_base_payload([{"role": "teacher", "content": "I think this deserves a 3."}]),
    )

    assert len(fake_database.dispute_turn_calls) == 1
    call = fake_database.dispute_turn_calls[0]
    assert str(call["essay_id"]) == ESSAY_ID
    assert call["caller_teacher_id"] == "test-teacher-sub"
    assert call["criterion_id"] == "bp1-evidence-1"
    assert call["teacher_message"] == "I think this deserves a 3."
    assert call["assistant_message"] == "I'd stand by the 2."


def test_dispute_endpoint_translates_teacher_and_assistant_roles_to_user_and_assistant(dispute_client):
    client, fake_client = dispute_client({"text": "ok", "tool_input": None})

    client.post(
        "/grade/dispute",
        json=_base_payload(
            [
                {"role": "teacher", "content": "Why is this a 2?"},
                {"role": "assistant", "content": "The quote lacks context."},
                {"role": "teacher", "content": "Sentence 2 gives the context though."},
            ]
        ),
    )

    sent_messages = fake_client.chat_calls[0]["messages"]
    assert sent_messages == [
        {"role": "user", "content": "Why is this a 2?"},
        {"role": "assistant", "content": "The quote lacks context."},
        {"role": "user", "content": "Sentence 2 gives the context though."},
    ]


def test_dispute_endpoint_rejects_a_transcript_that_doesnt_end_with_the_teacher(dispute_client):
    client, _ = dispute_client({"text": "ok", "tool_input": None})

    response = client.post(
        "/grade/dispute",
        json=_base_payload([{"role": "assistant", "content": "..."}]),
    )

    assert response.status_code == 422


def test_dispute_endpoint_returns_404_when_the_essay_doesnt_exist():
    fake_client = FakeGradingModelClient(chat_response={"text": "ok", "tool_input": None})
    app.dependency_overrides[get_grading_client] = lambda: fake_client
    app.dependency_overrides[get_database] = lambda: _RaisingDatabase(EssayNotFoundError("no such essay"))
    app.dependency_overrides[get_current_teacher] = lambda: TeacherIdentity(
        sub="test-teacher-sub", username="teacher@example.com"
    )
    client = TestClient(app)

    response = client.post(
        "/grade/dispute",
        json=_base_payload([{"role": "teacher", "content": "hi"}]),
    )

    assert response.status_code == 404
    app.dependency_overrides.clear()


def test_dispute_endpoint_returns_403_when_the_caller_doesnt_own_the_essay():
    fake_client = FakeGradingModelClient(chat_response={"text": "ok", "tool_input": None})
    app.dependency_overrides[get_grading_client] = lambda: fake_client
    app.dependency_overrides[get_database] = lambda: _RaisingDatabase(
        EssayAccessDeniedError("not your essay")
    )
    app.dependency_overrides[get_current_teacher] = lambda: TeacherIdentity(
        sub="test-teacher-sub", username="teacher@example.com"
    )
    client = TestClient(app)

    response = client.post(
        "/grade/dispute",
        json=_base_payload([{"role": "teacher", "content": "hi"}]),
    )

    assert response.status_code == 403
    app.dependency_overrides.clear()


def test_dispute_endpoint_rejects_requests_without_a_bearer_token(fake_database):
    fake_client = FakeGradingModelClient(chat_response={"text": "ok", "tool_input": None})
    app.dependency_overrides[get_grading_client] = lambda: fake_client
    app.dependency_overrides[get_database] = lambda: fake_database
    client = TestClient(app)

    response = client.post(
        "/grade/dispute",
        json=_base_payload([{"role": "teacher", "content": "hi"}]),
    )

    assert response.status_code == 401
    app.dependency_overrides.clear()
