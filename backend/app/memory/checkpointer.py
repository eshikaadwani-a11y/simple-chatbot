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
from collections.abc import Iterator
from contextlib import contextmanager

from app.config import get_settings

logger = logging.getLogger("learngraph")

_POOL = None
_ASYNC_POOL = None


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
        open=True,
        kwargs={"autocommit": True, "prepare_threshold": 0},
    )
    return _POOL


async def create_async_checkpointer() -> object:
    """Return an async-capable checkpointer for the app lifetime.

    The graph is executed via ``astream_events`` (async), so it requires an
    **async** checkpointer. A synchronous ``PostgresSaver`` does NOT implement the
    async checkpoint methods and raises at runtime under async execution — hence
    we use ``AsyncPostgresSaver`` backed by an ``AsyncConnectionPool`` here.

    Falls back to an in-memory saver when no database is configured (dev/tests)
    or if Postgres setup fails (so the service still boots; HITL resume just
    won't survive a restart).
    """
    settings = get_settings()
    if not settings.has_database:
        from langgraph.checkpoint.memory import MemorySaver

        logger.warning("DATABASE_URL not set; using in-memory checkpointer (non-durable).")
        return MemorySaver()

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from psycopg_pool import AsyncConnectionPool

        global _ASYNC_POOL
        _ASYNC_POOL = AsyncConnectionPool(
            conninfo=settings.database_url,
            max_size=10,
            open=False,
            kwargs={"autocommit": True, "prepare_threshold": 0},
        )
        await _ASYNC_POOL.open()
        checkpointer = AsyncPostgresSaver(_ASYNC_POOL)
        await checkpointer.setup()  # idempotent: creates checkpoint tables if missing
        logger.info("Async Postgres checkpointer ready.")
        return checkpointer
    except Exception as exc:  # noqa: BLE001
        from langgraph.checkpoint.memory import MemorySaver

        logger.error("Postgres checkpointer init failed (%s); falling back to in-memory.", exc)
        return MemorySaver()


async def close_pools() -> None:
    """Close any open connection pools at shutdown."""
    global _ASYNC_POOL, _POOL
    if _ASYNC_POOL is not None:
        await _ASYNC_POOL.close()
        _ASYNC_POOL = None
    if _POOL is not None:
        _POOL.close()
        _POOL = None


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
