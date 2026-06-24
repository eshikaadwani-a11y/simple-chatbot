"""Admin analytics route — usage, cost, and engagement metrics.

Protected by ``require_admin`` (an explicit email allow-list in production).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from app import analytics
from app.api.deps import CurrentUser, require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/analytics")
async def admin_analytics(_: CurrentUser = Depends(require_admin)) -> dict:
    """Aggregate usage analytics + cost for the admin dashboard."""
    return await run_in_threadpool(analytics.aggregate_admin)
