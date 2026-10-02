"""Test setup.

- Postgres: real Postgres + pgvector is required (hybrid search is SQL). CI uses a
  `pgvector/pgvector` service container via TEST_DATABASE_URL; locally we fall back to the
  `pgserver` wheel so tests run without Docker.
- LLM and embeddings are always fakes: tests are fast, free, offline and deterministic.
"""

import os

# Must be set before any app module reads settings.
os.environ.update(
    {
        "ENV": "test",
        "LLM_PRIMARY": "fake",
        "LLM_FALLBACK": "none",
        "EMBEDDING_PROVIDER": "hash",
        "RERANKER_ENABLED": "false",
        "INGESTION_MODE": "inline",
        "RATE_LIMIT_ENABLED": "false",
        "QUERY_REWRITE_ENABLED": "true",
        "VECTOR_MIN_SIMILARITY": "0.05",
        "REDIS_URL": "",
        "FIRST_ADMIN_EMAIL": "admin@example.com",
        "LOG_LEVEL": "WARNING",
    }
)


def _test_database_url() -> str:
    if url := os.environ.get("TEST_DATABASE_URL"):
        return url
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from localdb import start  # type: ignore[import-not-found]

    return start("techprep_test")


os.environ["DATABASE_URL"] = _test_database_url()

import tempfile  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="techprep-test-uploads-")

from app.core.config import get_settings  # noqa: E402
from app.db.session import SessionLocal, get_engine  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _migrated_database():
    """Run the real Alembic migrations once per session (tests the migrations too)."""
    from alembic.config import Config

    from alembic import command

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    with get_engine().begin() as conn:
        names = conn.scalars(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
            )
        ).all()
        if names:
            conn.execute(text(f"TRUNCATE {', '.join(names)} RESTART IDENTITY CASCADE"))


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def settings():
    return get_settings()


def register_and_login(client: TestClient, email: str, password: str = "password123") -> dict:
    r = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    r = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def auth_headers(client):
    return register_and_login(client, "alice@example.com")


@pytest.fixture
def other_auth_headers(client):
    return register_and_login(client, "bob@example.com")
