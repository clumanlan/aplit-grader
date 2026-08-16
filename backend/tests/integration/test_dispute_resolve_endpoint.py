import uuid

import pytest
from fastapi.testclient import TestClient

from aplit_grader.api.auth import TeacherIdentity, get_current_teacher
from aplit_grader.api.routes import get_database
from aplit_grader.main import app
from aplit_grader.storage.db import DisputeNotFoundError, RawGradeMismatchError
from tests.fixtures.fake_database import FakeDatabase

ESSAY_ID = str(uuid.uuid4())
RAW_GRADE_ID = str(uuid.uuid4())


class _RaisingDatabase(FakeDatabase):
    def __init__(self, error: Exception):
        super().__init__()
        self._error = error

    async def resolve_dispute(self, **kwargs):
        self.resolve_calls.append(kwargs)
        raise self._error


@pytest.fixture
def resolve_client():
    def _make(database):
        app.dependency_overrides[get_database] = lambda: database
        app.dependency_overrides[get_current_teacher] = lambda: TeacherIdentity(
            sub="test-teacher-sub", username="teacher@example.com"
        )
        return TestClient(app)

    yield _make
    app.dependency_overrides.clear()


def test_resolve_endpoint_returns_the_accepted_grade_for_a_correction(resolve_client):
    fake_database = FakeDatabase()
    fake_database.resolve_response = (uuid.uuid4(), 3, False)
    client = resolve_client(fake_database)

    response = client.post(
        "/grade/dispute/resolve",
        json={
            "essay_id": ESSAY_ID,
            "criterion_id": "bp1-evidence-1",
            "resolution": "corrected",
            "raw_grade_id": RAW_GRADE_ID,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 3
    assert body["missing"] is False
    assert len(fake_database.resolve_calls) == 1
    call = fake_database.resolve_calls[0]
    assert str(call["essay_id"]) == ESSAY_ID
    assert call["resolution"] == "corrected"
    assert str(call["raw_grade_id"]) == RAW_GRADE_ID


def test_resolve_endpoint_rejects_corrected_without_a_raw_grade_id(resolve_client):
    client = resolve_client(FakeDatabase())

    response = client.post(
        "/grade/dispute/resolve",
        json={"essay_id": ESSAY_ID, "criterion_id": "bp1-evidence-1", "resolution": "corrected"},
    )

    assert response.status_code == 422


def test_resolve_endpoint_allows_kept_original_without_a_raw_grade_id(resolve_client):
    fake_database = FakeDatabase()
    fake_database.resolve_response = (uuid.uuid4(), 2, False)
    client = resolve_client(fake_database)

    response = client.post(
        "/grade/dispute/resolve",
        json={"essay_id": ESSAY_ID, "criterion_id": "bp1-evidence-1", "resolution": "kept_original"},
    )

    assert response.status_code == 200
    assert response.json()["score"] == 2


def test_resolve_endpoint_returns_404_when_there_is_no_open_dispute(resolve_client):
    client = resolve_client(_RaisingDatabase(DisputeNotFoundError("no open dispute")))

    response = client.post(
        "/grade/dispute/resolve",
        json={"essay_id": ESSAY_ID, "criterion_id": "bp1-evidence-1", "resolution": "kept_original"},
    )

    assert response.status_code == 404


def test_resolve_endpoint_returns_400_when_the_raw_grade_id_is_mismatched(resolve_client):
    client = resolve_client(_RaisingDatabase(RawGradeMismatchError("mismatched")))

    response = client.post(
        "/grade/dispute/resolve",
        json={
            "essay_id": ESSAY_ID,
            "criterion_id": "bp1-evidence-1",
            "resolution": "corrected",
            "raw_grade_id": RAW_GRADE_ID,
        },
    )

    assert response.status_code == 400


def test_resolve_endpoint_rejects_requests_without_a_bearer_token():
    app.dependency_overrides[get_database] = lambda: FakeDatabase()
    client = TestClient(app)

    response = client.post(
        "/grade/dispute/resolve",
        json={"essay_id": ESSAY_ID, "criterion_id": "bp1-evidence-1", "resolution": "kept_original"},
    )

    assert response.status_code == 401
    app.dependency_overrides.clear()
