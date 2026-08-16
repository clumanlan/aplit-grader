from typing import Any

import pytest
from fastapi.testclient import TestClient

from aplit_grader.api.auth import TeacherIdentity, get_current_teacher
from aplit_grader.api.routes import get_grading_client, get_result_logger
from aplit_grader.main import app
from aplit_grader.schemas.requests import GradeResponse
from aplit_grader.services.pipeline import PipelineStepEvent
from aplit_grader.services.rubric import RUBRIC
from aplit_grader.storage.result_logger import ResultLogger, RunContext
from tests.fixtures.canned_pipeline_responses import happy_path_responses
from tests.fixtures.fake_grading_client import FakeGradingModelClient
from tests.fixtures.sample_essays import (
    GATSBY_ASSIGNMENT_PROMPT,
    GATSBY_FOUR_SENTENCE_ESSAY,
)

GATSBY_CLASS_ID = "Period 3 — AP Lit"


class _RecordingResultLogger(ResultLogger):
    def __init__(self):
        self.step_calls: list[tuple[RunContext, PipelineStepEvent]] = []
        self.final_result_calls: list[tuple[RunContext, str, GradeResponse]] = []

    async def log_step(self, context: RunContext, event: PipelineStepEvent) -> None:
        self.step_calls.append((context, event))

    async def log_final_result(
        self, context: RunContext, essay_text: str, result: GradeResponse
    ) -> str:
        self.final_result_calls.append((context, essay_text, result))
        return f"local-test/{context.run_id}/final_result.json"


@pytest.fixture
def recording_logger():
    return _RecordingResultLogger()


@pytest.fixture
def client_factory():
    """Overrides get_grading_client with a FakeGradingModelClient built from the given responses."""

    def _make(responses: list[dict[str, Any]]):
        return FakeGradingModelClient(responses=responses)

    return _make


@pytest.fixture
def test_client(recording_logger):
    def _make(fake_grading_client):
        app.dependency_overrides[get_grading_client] = lambda: fake_grading_client
        app.dependency_overrides[get_result_logger] = lambda: recording_logger
        app.dependency_overrides[get_current_teacher] = lambda: TeacherIdentity(
            sub="test-teacher-sub", username="teacher@example.com"
        )
        return TestClient(app)

    yield _make
    app.dependency_overrides.clear()


def test_grade_endpoint_returns_all_fourteen_criteria_on_happy_path(test_client, client_factory):
    fake_client = client_factory(happy_path_responses())
    client = test_client(fake_client)

    response = client.post(
        "/grade",
        json={
            "essay_text": GATSBY_FOUR_SENTENCE_ESSAY,
            "assignment_prompt": GATSBY_ASSIGNMENT_PROMPT,
            "class_id": GATSBY_CLASS_ID,
            "student_name": "Jane Doe",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert {c["criterion_id"] for c in body["criteria"]} == set(RUBRIC)


def test_grade_endpoint_logs_each_step_and_the_final_result(
    test_client, client_factory, recording_logger
):
    fake_client = client_factory(happy_path_responses())
    client = test_client(fake_client)

    client.post(
        "/grade",
        json={
            "essay_text": GATSBY_FOUR_SENTENCE_ESSAY,
            "assignment_prompt": GATSBY_ASSIGNMENT_PROMPT,
            "class_id": GATSBY_CLASS_ID,
        },
    )

    sources_logged = [event.source for _, event in recording_logger.step_calls]
    assert sources_logged == ["segmentation", "thesis", "body_1", "body_2", "conclusion"]
    assert len(recording_logger.final_result_calls) == 1


def test_grade_endpoint_returns_502_with_failed_step_when_the_pipeline_aborts(
    test_client, client_factory
):
    fake_client = client_factory([{"unexpected_shape": True}])
    client = test_client(fake_client)

    response = client.post(
        "/grade",
        json={
            "essay_text": GATSBY_FOUR_SENTENCE_ESSAY,
            "assignment_prompt": GATSBY_ASSIGNMENT_PROMPT,
            "class_id": GATSBY_CLASS_ID,
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"]["failed_step"] == "segmentation"


def test_grade_endpoint_rejects_empty_essay_text(test_client, client_factory):
    fake_client = client_factory(happy_path_responses())
    client = test_client(fake_client)

    response = client.post(
        "/grade",
        json={
            "essay_text": "",
            "assignment_prompt": GATSBY_ASSIGNMENT_PROMPT,
            "class_id": GATSBY_CLASS_ID,
        },
    )

    assert response.status_code == 422


def test_grade_endpoint_forwards_assignment_prompt_to_the_pipeline(test_client, client_factory):
    fake_client = client_factory(happy_path_responses())
    client = test_client(fake_client)

    client.post(
        "/grade",
        json={
            "essay_text": GATSBY_FOUR_SENTENCE_ESSAY,
            "assignment_prompt": GATSBY_ASSIGNMENT_PROMPT,
            "class_id": GATSBY_CLASS_ID,
        },
    )

    thesis_call = next(c for c in fake_client.calls if c["tool_name"] == "submit_thesis_grade")
    assert GATSBY_ASSIGNMENT_PROMPT in thesis_call["user_prompt"]


def test_grade_endpoint_rejects_empty_assignment_prompt(test_client, client_factory):
    fake_client = client_factory(happy_path_responses())
    client = test_client(fake_client)

    response = client.post(
        "/grade",
        json={
            "essay_text": GATSBY_FOUR_SENTENCE_ESSAY,
            "assignment_prompt": "",
            "class_id": GATSBY_CLASS_ID,
        },
    )

    assert response.status_code == 422


def test_grade_endpoint_rejects_empty_class_id(test_client, client_factory):
    fake_client = client_factory(happy_path_responses())
    client = test_client(fake_client)

    response = client.post(
        "/grade",
        json={
            "essay_text": GATSBY_FOUR_SENTENCE_ESSAY,
            "assignment_prompt": GATSBY_ASSIGNMENT_PROMPT,
            "class_id": "",
        },
    )

    assert response.status_code == 422


def test_grade_endpoint_logs_the_authenticated_teacher_and_slugified_class(
    test_client, client_factory, recording_logger
):
    fake_client = client_factory(happy_path_responses())
    client = test_client(fake_client)

    client.post(
        "/grade",
        json={
            "essay_text": GATSBY_FOUR_SENTENCE_ESSAY,
            "assignment_prompt": GATSBY_ASSIGNMENT_PROMPT,
            "class_id": GATSBY_CLASS_ID,
        },
    )

    context, _ = recording_logger.step_calls[0]
    assert context.teacher_id == "test-teacher-sub"
    assert context.class_slug == "period-3-ap-lit"


def test_grade_endpoint_rejects_requests_without_a_bearer_token(recording_logger, client_factory):
    # Deliberately does not use the `test_client` fixture — that fixture overrides
    # get_current_teacher, which is exactly the dependency this test checks is
    # actually enforced when nothing overrides it.
    fake_client = client_factory(happy_path_responses())
    app.dependency_overrides[get_grading_client] = lambda: fake_client
    app.dependency_overrides[get_result_logger] = lambda: recording_logger
    client = TestClient(app)

    response = client.post(
        "/grade",
        json={
            "essay_text": GATSBY_FOUR_SENTENCE_ESSAY,
            "assignment_prompt": GATSBY_ASSIGNMENT_PROMPT,
            "class_id": GATSBY_CLASS_ID,
        },
    )

    assert response.status_code == 401
    app.dependency_overrides.clear()
