"""FastAPI application entrypoint for the LearnGraph backend."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.models import default_model_name, list_models
from app.api import routes_auth, routes_chat, routes_progress, routes_resume
from app.config import get_settings
from app.observability import configure_observability
from app.security import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    register_error_handlers,
    validate_environment,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("learngraph")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_observability()
    validate_environment(settings)
    logger.info(
        "Starting %s | model=%s | supabase=%s | db=%s",
        settings.app_name,
        default_model_name(),
        settings.has_supabase,
        settings.has_database,
    )
    # Compile the agent graph with an async-capable checkpointer.
    try:
        from app.agents.runtime import init_graph

        await init_graph()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Graph init deferred: %s", exc)
    yield
    try:
        from app.agents.runtime import shutdown

        await shutdown()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Shutdown cleanup error: %s", exc)
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
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Security middleware (outermost runs first): rate limiting then headers.
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        per_minute=settings.rate_limit_per_minute,
        heavy_per_minute=settings.rate_limit_heavy_per_minute,
    )

    register_error_handlers(app)

    app.include_router(routes_auth.router)
    app.include_router(routes_chat.router)
    app.include_router(routes_progress.router)
    app.include_router(routes_resume.router)

    @app.get("/health", tags=["meta"])
    async def health() -> dict:
        return {"status": "ok", "service": settings.app_name}

    @app.get("/meta/models", tags=["meta"])
    async def models() -> dict:
        return {"default": default_model_name(), "available": list_models()}

    return app


app = create_app()
