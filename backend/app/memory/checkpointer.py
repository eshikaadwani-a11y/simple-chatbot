"""Short-term memory — LangGraph checkpointer (workflow persistence/recovery).

A checkpointer snapshots graph state after every step, keyed by ``thread_id``.
This gives us:
  * conversation continuity within a session (short-term memory),
  * workflow recovery — an interrupted/crashed run resumes from its last step,
  * human-in-the-loop — the graph can pause at an ``interrupt()`` and resume later.

We use the Postgres checkpointer when ``DATABASE_URL`` is set, otherwise an
in-memory saver for local development.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from app.config import get_settings

logger = logging.getLogger("learngraph")

_POOL = None


def _get_pool():
    """Create (once) a psycopg connection pool for the checkpointer."""
    global _POOL
    if _POOL is not None:
        return _POOL
    from psycopg_pool import ConnectionPool

    settings = get_settings()
    _POOL = ConnectionPool(
        conninfo=settings.database_url,
        max_size=10,
        kwargs={"autocommit": True, "prepare_threshold": 0},
    )
    return _POOL


def create_checkpointer() -> object:
    """Return a long-lived checkpointer instance for the app lifetime.

    Unlike ``get_checkpointer`` (a context manager for scripts/tests), this keeps
    the underlying connection pool open for the duration of the process and is
    intended to be called once at FastAPI startup.
    """
    settings = get_settings()
    if not settings.has_database:
        from langgraph.checkpoint.memory import MemorySaver

        logger.warning("DATABASE_URL not set; using in-memory checkpointer (non-durable).")
        return MemorySaver()

    from langgraph.checkpoint.postgres import PostgresSaver

    checkpointer = PostgresSaver(_get_pool())
    try:
        checkpointer.setup()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Checkpointer setup skipped: %s", exc)
    return checkpointer


@contextmanager
def get_checkpointer() -> Iterator[object]:
    """Yield a checkpointer instance, setting up tables on first use.

    Usage:
        with get_checkpointer() as cp:
            graph = build_graph(checkpointer=cp)
    """
    settings = get_settings()
    if not settings.has_database:
        from langgraph.checkpoint.memory import MemorySaver

        logger.warning("DATABASE_URL not set; using in-memory checkpointer (non-durable).")
        yield MemorySaver()
        return

    from langgraph.checkpoint.postgres import PostgresSaver

    pool = _get_pool()
    checkpointer = PostgresSaver(pool)
    try:
        checkpointer.setup()  # idempotent: creates checkpoint tables if missing
    except Exception as exc:  # noqa: BLE001
        logger.warning("Checkpointer setup skipped: %s", exc)
    yield checkpointer
