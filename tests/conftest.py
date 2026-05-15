"""
Shared test fixtures for NetScout API and unit tests.

Uses a dedicated PostgreSQL database (default: ``netscout`` user, DB ``netscout_test``)
so JSONB/UUID models match production. Override with ``TEST_DATABASE_URL``.

The database is created automatically if it does not exist (requires a server
connection to the ``postgres`` maintenance DB with the same credentials).

Between tests, core tables are truncated with ``RESTART IDENTITY CASCADE`` for isolation.
"""

from __future__ import annotations

import os
import sys
from typing import Generator
from urllib.parse import urlparse, urlunparse

# ---- Must run BEFORE any import of app.db.database / settings ----
_DEFAULT_TEST_DB = "postgresql://netscout:netscout@127.0.0.1:5432/netscout_test"


def _ensure_postgres_database_exists(database_url: str) -> None:
    """CREATE DATABASE if missing (PostgreSQL only)."""
    raw = database_url.replace("postgresql+psycopg2://", "postgresql://")
    parsed = urlparse(raw)
    if parsed.scheme not in ("postgresql", "postgres"):
        return
    dbname = (parsed.path or "").strip("/").split("?")[0]
    if not dbname:
        return
    admin = urlunparse(
        (parsed.scheme, parsed.netloc, "/postgres", "", parsed.query, parsed.fragment)
    )
    admin = admin.replace("postgresql://", "postgresql+psycopg2://", 1)
    from sqlalchemy import create_engine, text

    eng = create_engine(
        admin,
        isolation_level="AUTOCOMMIT",
        connect_args={"connect_timeout": 5},
    )
    try:
        with eng.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :n"),
                {"n": dbname},
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{dbname}"'))
    finally:
        eng.dispose()


_test_db_url = os.getenv("TEST_DATABASE_URL", _DEFAULT_TEST_DB)
try:
    _ensure_postgres_database_exists(_test_db_url)
except OSError as exc:
    raise RuntimeError(
        f"Cannot prepare test database at {_test_db_url!r}: {exc}. "
        "Start PostgreSQL (e.g. docker compose up -d) or set TEST_DATABASE_URL."
    ) from exc
except Exception as exc:
    raise RuntimeError(
        f"Cannot prepare test database at {_test_db_url!r}: {exc}. "
        "Ensure role can create DB or create database manually."
    ) from exc

os.environ["DATABASE_URL"] = _test_db_url
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-netscout-tests-only")

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BACKEND = os.path.join(_ROOT, "backend")
for _p in (_ROOT, _BACKEND):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def _setup_test_db() -> Generator[None, None, None]:
    """Create all ORM tables once on the test PostgreSQL database."""
    from app.db.database import init_db

    init_db()
    yield


@pytest.fixture(autouse=True)
def _truncate_tables() -> Generator[None, None, None]:
    """Fresh data for every test (committed API work from previous test is cleared)."""
    from sqlalchemy import text
    from app.db.database import engine

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE users RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def db() -> Generator:
    """Per-test SQLAlchemy session (same engine as the FastAPI app)."""
    from app.db.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _make_client(db_session):
    """Build a TestClient that overrides get_db with the given session."""
    from app.main import app
    from app.db.database import get_db

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db

    with (
        patch("app.main.init_db"),
        patch("app.services.scheduler_service.start_scheduler"),
        patch(
            "app.services.scheduler_service.get_scheduler",
            return_value=MagicMock(running=False),
        ),
        patch("app.services.neo4j_service.is_neo4j_available", return_value=False),
        # investigation_service binds is_neo4j_available at import time; patching
        # neo4j_service alone does not update that name (stale reference).
        patch(
            "app.services.investigation_service.is_neo4j_available",
            return_value=True,
        ),
        patch("app.services.neo4j_service.close_driver"),
    ):
        with TestClient(app, raise_server_exceptions=True) as client:
            yield client

    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client(db):
    yield from _make_client(db)


@pytest.fixture
def test_user(db):
    """Create a regular test user and clean up after the test."""
    from app.db.models import User
    from app.services.auth_service import get_password_hash

    user = User(
        email="testuser@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpassword123"),
        email_notifications_enabled=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user


@pytest.fixture
def auth_headers(test_user):
    """Return Authorization header dict for the test user."""
    from app.services.auth_service import create_access_token

    token = create_access_token({"sub": str(test_user.id), "email": test_user.email})
    return {"Authorization": f"Bearer {token}"}
