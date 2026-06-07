"""Shared test fixtures.

Unit tests need no database. Integration tests (marked `@pytest.mark.integration`)
need a reachable Postgres; they are skipped automatically when none is available.

Test isolation: the integration database is rebuilt from migrations once per
session (DROP/CREATE SCHEMA public), and every table is truncated before each
test. Point this at a disposable database via TEST_DATABASE_URL — it WILL drop
the public schema.
"""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

import pytest

# --- Environment must be set before app modules read settings ---------------

# Route blob writes to a throwaway dir so tests never touch ./.storage.
_TMP_STORAGE = tempfile.mkdtemp(prefix="rppc-test-storage-")
os.environ["LOCAL_STORAGE_ROOT"] = _TMP_STORAGE
os.environ.setdefault("DEV_BEARER_TOKEN", "test-token")
os.environ.setdefault("JOB_QUEUE_BACKEND", "inproc")

# Integration DB target (disposable!). Falls back to DATABASE_URL.
_TEST_DB_URL = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
if _TEST_DB_URL:
    os.environ["DATABASE_URL"] = _TEST_DB_URL

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"

DATA_TABLES = [
    "usage_events", "exports", "feedback_events",
    "audio_mixes", "audio_segments", "qa_reports",
    "segment_evidence_links", "script_segments", "script_versions",
    "role_context_cards", "discussion_plans", "episode_personas", "episodes",
    "source_claims",
    "source_chunks", "sources", "projects", "users",
    "persona_canon_chunks", "persona_corpus_docs", "persona_versions",
    "persona_assets",
]


def _can_connect() -> bool:
    if not _TEST_DB_URL:
        return False
    try:
        import psycopg

        with psycopg.connect(_TEST_DB_URL, connect_timeout=2):
            return True
    except Exception:
        return False


DB_AVAILABLE = _can_connect()


def _split_statements(sql: str) -> list[str]:
    """Naive SQL splitter for our comment-only, function-free migrations."""
    no_comments = re.sub(r"--[^\n]*", "", sql)
    return [s.strip() for s in no_comments.split(";") if s.strip()]


@pytest.fixture(scope="session")
def migrated_db():
    if not DB_AVAILABLE:
        pytest.skip("no test database available (set TEST_DATABASE_URL/DATABASE_URL)")
    import psycopg

    with psycopg.connect(_TEST_DB_URL, autocommit=True) as conn:
        conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
        conn.execute("CREATE SCHEMA public")
        for path in sorted(MIGRATIONS_DIR.glob("0[0-9][0-9]_*.sql")):
            if path.name.startswith("000"):
                continue
            for stmt in _split_statements(path.read_text()):
                conn.execute(stmt)
    yield


@pytest.fixture
def clean_db(migrated_db):
    import psycopg

    with psycopg.connect(_TEST_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE " + ", ".join(DATA_TABLES) + " RESTART IDENTITY CASCADE"
        )
    yield


@pytest.fixture
def client(clean_db):
    """FastAPI TestClient against the migrated, truncated DB."""
    from fastapi.testclient import TestClient

    from app.db import close_pool
    from app.main import app

    with TestClient(app) as c:
        yield c
    close_pool()


@pytest.fixture
def auth():
    return {"Authorization": f"Bearer {os.environ['DEV_BEARER_TOKEN']}"}


@pytest.fixture
def seeded_personas(clean_db):
    """Import the persona YAML seeds into the (clean) test DB."""
    from app.personas_import import import_personas

    return import_personas()
