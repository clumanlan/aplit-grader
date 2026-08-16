import os

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from aplit_grader.storage.db import Database
from aplit_grader.storage.models import Base

load_dotenv()

_TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg2://aplit_grader:local_dev_only@localhost:5432/aplit_grader"
)

_APP_TABLES = "dispute_messages, disputes, accepted_grades, raw_grades, essays, sessions"


def _database_reachable() -> bool:
    try:
        engine = create_engine(_TEST_DATABASE_URL)
        with engine.connect():
            pass
        engine.dispose()
        return True
    except OperationalError:
        return False


@pytest.fixture(scope="session")
def db_engine():
    """Real Postgres (docker compose up -d at repo root), tables created once per
    test session. Skips every test that depends on this — directly or via the
    `database` fixture — when Postgres isn't reachable, rather than failing.
    """
    if not _database_reachable():
        pytest.skip(f"Postgres not reachable at {_TEST_DATABASE_URL} — run `docker compose up -d`")
    engine = create_engine(_TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def database(db_engine):
    """A Database instance against the real test Postgres, truncated after each test
    for isolation (kept simple/blunt rather than per-test transactions+rollback,
    since Database opens its own sessions/connections internally).
    """
    db = Database(_TEST_DATABASE_URL)
    yield db
    with db_engine.connect() as conn:
        conn.execute(text(f"TRUNCATE {_APP_TABLES} RESTART IDENTITY CASCADE"))
        conn.commit()
