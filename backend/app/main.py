"""FastAPI application entrypoint for the LearnGraph backend."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.models import default_model_name, list_models
from app.api import routes_auth, routes_chat, routes_progress
from app.config import get_settings
from app.observability import configure_observability

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("learngraph")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_observability()
    logger.info(
        "Starting %s | model=%s | supabase=%s | db=%s",
        settings.app_name,
        default_model_name(),
        settings.has_supabase,
        settings.has_database,
    )
    # Warm up the compiled graph so the first request isn't slow.
    try:
        from app.agents.runtime import get_graph

        get_graph()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Graph warm-up deferred: %s", exc)
    yield
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="LearnGraph API",
        version="1.0.0",
        description="Multi-agent AI learning platform (GPT-5 + LangGraph).",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(routes_auth.router)
    app.include_router(routes_chat.router)
    app.include_router(routes_progress.router)

    @app.get("/health", tags=["meta"])
    async def health() -> dict:
        return {"status": "ok", "service": settings.app_name}

    @app.get("/meta/models", tags=["meta"])
    async def models() -> dict:
        return {"default": default_model_name(), "available": list_models()}

    return app


app = create_app()
