import os
from pathlib import Path

import pytest
from alembic.config import Config
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from alembic import command
from aplit_grader.storage.db import Database

load_dotenv()

_TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg2://aplit_grader:local_dev_only@localhost:5432/aplit_grader"
)
_ALEMBIC_INI = Path(__file__).parent.parent / "alembic.ini"

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
    """Real Postgres (docker compose up -d at repo root), migrated to head once per
    test session via the real Alembic migrations (not Base.metadata.create_all) —
    so the test suite actually exercises the same migration path a real deploy
    would, and a migration that doesn't match the ORM models gets caught here.
    Skips every test that depends on this — directly or via the `database`
    fixture — when Postgres isn't reachable, rather than failing.
    """
    if not _database_reachable():
        pytest.skip(f"Postgres not reachable at {_TEST_DATABASE_URL} — run `docker compose up -d`")
    alembic_cfg = Config(str(_ALEMBIC_INI))
    alembic_cfg.set_main_option("sqlalchemy.url", _TEST_DATABASE_URL)
    command.upgrade(alembic_cfg, "head")
    engine = create_engine(_TEST_DATABASE_URL)
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
