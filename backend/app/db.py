"""Database access.

Migrations (backend/migrations/*.sql) are the single source of truth for the
schema (design §24.3). The app talks to Postgres through a small psycopg
connection pool and raw SQL in app/repositories/, rather than an ORM, to avoid
a second schema definition drifting from the migrations.

The pool is created lazily so the app still imports without a database present
(useful for the in-process demo path and for unit tests).
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional

from .config import get_settings

try:  # psycopg is a runtime dep, but keep import soft for import-only contexts
    import psycopg
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool
except Exception:  # pragma: no cover
    psycopg = None  # type: ignore
    ConnectionPool = None  # type: ignore
    dict_row = None  # type: ignore

_pool: "Optional[ConnectionPool]" = None


def get_pool() -> "ConnectionPool":
    global _pool
    if psycopg is None:
        raise RuntimeError(
            "psycopg is not installed. Run `pip install -e .` in backend/."
        )
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=get_settings().database_url,
            min_size=1,
            max_size=10,
            kwargs={"row_factory": dict_row, "autocommit": False},
            open=True,
        )
    return _pool


@contextmanager
def get_conn() -> Iterator["psycopg.Connection"]:
    """Yield a pooled connection, committing on success and rolling back on error."""
    pool = get_pool()
    with pool.connection() as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
