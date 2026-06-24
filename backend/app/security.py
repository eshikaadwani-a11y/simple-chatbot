"""Production security: rate limiting, secure headers, env validation, errors.

These are intentionally dependency-free (no external rate-limit library) so the
service stays lean. The rate limiter is per-process; behind multiple workers use
a shared store (e.g. Redis) — see the note in ``RateLimitMiddleware``.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_429_TOO_MANY_REQUESTS, HTTP_500_INTERNAL_SERVER_ERROR

from app.config import Settings

logger = logging.getLogger("learngraph")

# Paths exempt from rate limiting (liveness / cheap metadata).
_EXEMPT_PREFIXES = ("/health", "/meta", "/docs", "/openapi.json")
# Expensive paths get a tighter budget (they trigger LLM calls / PDF parsing).
_HEAVY_PREFIXES = ("/chat", "/resume")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach a conservative set of security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        headers = response.headers
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        headers.setdefault(
            "Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload"
        )
        # This is a JSON API; disallow embedding/active content by default.
        headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter keyed by client IP + path category.

    NOTE: state is in-process. For horizontally-scaled deployments, back this
    with Redis (or use an API gateway) so limits are enforced cluster-wide.
    """

    def __init__(self, app, *, per_minute: int, heavy_per_minute: int):
        super().__init__(app)
        self.per_minute = per_minute
        self.heavy_per_minute = heavy_per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._since_sweep = 0

    def _client_ip(self, request: Request) -> str:
        # Respect the first hop of X-Forwarded-For when behind a proxy/LB.
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _sweep(self, cutoff: float) -> None:
        """Evict keys whose window is fully expired (prevents unbounded growth)."""
        stale = [k for k, w in self._hits.items() if not w or w[-1] < cutoff]
        for k in stale:
            del self._hits[k]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if request.method == "OPTIONS" or path.startswith(_EXEMPT_PREFIXES):
            return await call_next(request)

        heavy = path.startswith(_HEAVY_PREFIXES)
        limit = self.heavy_per_minute if heavy else self.per_minute
        bucket = "heavy" if heavy else "std"
        key = f"{self._client_ip(request)}:{bucket}"

        now = time.monotonic()
        cutoff = now - 60.0

        # Periodic sweep so single-hit clients don't leak memory forever.
        self._since_sweep += 1
        if self._since_sweep >= 1000:
            self._since_sweep = 0
            self._sweep(cutoff)

        window = self._hits[key]
        while window and window[0] < cutoff:
            window.popleft()

        if len(window) >= limit:
            retry = max(1, int(60 - (now - window[0])))
            return JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Please slow down."},
                headers={"Retry-After": str(retry)},
            )

        window.append(now)
        return await call_next(request)


def register_error_handlers(app: FastAPI) -> None:
    """Global handlers that never leak stack traces to clients."""

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422, content={"detail": "Invalid request.", "errors": exc.errors()}
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error."},
        )


def validate_environment(settings: Settings) -> None:
    """Fail fast in production if critical configuration is missing.

    In non-production environments we only warn, so the stack stays runnable for
    local development with the built-in fallbacks.
    """
    has_model_key = any(
        [
            settings.openai_api_key,
            settings.anthropic_api_key,
            settings.google_api_key,
            settings.deepseek_api_key,
        ]
    )
    checks = {
        "an LLM provider key (OPENAI_API_KEY/...)": has_model_key,
        "SUPABASE_URL": bool(settings.supabase_url),
        "SUPABASE_SERVICE_ROLE_KEY": bool(settings.supabase_service_role_key),
        "SUPABASE_JWT_SECRET": bool(settings.supabase_jwt_secret),
        "DATABASE_URL": bool(settings.database_url),
    }
    missing = [name for name, ok in checks.items() if not ok]

    is_prod = settings.environment.lower() in ("production", "prod")
    if missing and is_prod:
        raise RuntimeError(
            "Refusing to start in production with missing configuration: " + ", ".join(missing)
        )
    if missing:
        logger.warning("Running with missing config (dev fallbacks active): %s", ", ".join(missing))
