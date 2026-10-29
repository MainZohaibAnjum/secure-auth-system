"""Shared test setup: a separate, throwaway database and ready-made test users."""
import os
from pathlib import Path

import pytest
from dotenv import dotenv_values

# ---------- Point the app at the TEST database (before any app code is imported) ----------

BACKEND_DIR = Path(__file__).resolve().parent.parent
_env = dotenv_values(BACKEND_DIR / ".env")
TEST_DATABASE_NAME = _env.get("TEST_DATABASE_NAME")

if not TEST_DATABASE_NAME:
    raise RuntimeError("Add TEST_DATABASE_NAME to backend/.env before running the tests")
if TEST_DATABASE_NAME == _env.get("DATABASE_NAME"):
    # The tests delete this database, so it must never be the real one
    raise RuntimeError("TEST_DATABASE_NAME must be different from DATABASE_NAME")

os.environ["DATABASE_NAME"] = TEST_DATABASE_NAME

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402

PASSWORD = "correct-horse-battery-staple"


@pytest.fixture(scope="session", autouse=True)
def test_database():
    """Create a fresh test database once, build the tables with Alembic, delete it at the end."""
    # Connect to Postgres's built-in "postgres" database to create/drop ours
    admin = create_engine(
        settings.database_url.rsplit("/", 1)[0] + "/postgres", isolation_level="AUTOCOMMIT"
    )
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DATABASE_NAME}"'))
        conn.execute(text(f'CREATE DATABASE "{TEST_DATABASE_NAME}"'))

    # Running the real migrations also tests that they work
    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")

    yield

    engine.dispose()  # close the app's connections, or Postgres refuses to drop the database
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DATABASE_NAME}"'))
    admin.dispose()


@pytest.fixture(autouse=True)
def empty_tables():
    """Every test starts with no users and no sessions."""
    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE users, refresh_sessions"))


@pytest.fixture(autouse=True)
def rate_limits_off():
    """Tests send many requests quickly, so limits are off (test_rate_limit.py turns them on)."""
    limiter.reset()
    limiter.enabled = False


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def user(client):
    """A signed-up user. Returns the email and password."""
    creds = {"email": "alice@example.com", "password": PASSWORD}
    assert client.post("/auth/signup", json=creds).status_code == 201
    return creds


@pytest.fixture
def auth_headers(client, user):
    """Authorization header for the logged-in user."""
    token = client.post("/auth/login", json=user).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
