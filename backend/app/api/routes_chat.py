"""Chat routes — token-by-token streaming + human-in-the-loop resume."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.agents.runtime import resume_after_approval, stream_response
from app.api.deps import CurrentUser, get_current_user
from app.api.schemas import ChatRequest, ResumeRequest

router = APIRouter(prefix="/chat", tags=["chat"])


def _sse(event: dict) -> dict:
    """Format an agent event as a Server-Sent Event payload."""
    return {"event": event.get("type", "message"), "data": json.dumps(event)}


# Disable proxy/CDN buffering so tokens flush immediately (Railway/Nginx/Vercel).
_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


@router.post("/stream")
async def chat_stream(body: ChatRequest, user: CurrentUser = Depends(get_current_user)):
    """Stream the agent's response as Server-Sent Events.

    Event types: token, tool, route, interrupt, error, done.
    """

    async def event_generator():
        async for event in stream_response(
            user_id=user.user_id, thread_id=body.thread_id, message=body.message
        ):
            yield _sse(event)

    return EventSourceResponse(event_generator(), headers=_SSE_HEADERS)


@router.post("/resume")
async def chat_resume(body: ResumeRequest, user: CurrentUser = Depends(get_current_user)):
    """Resume an interrupted (human-in-the-loop) run after approval/rejection."""

    async def event_generator():
        async for event in resume_after_approval(
            user_id=user.user_id, thread_id=body.thread_id, approved=body.approved
        ):
            yield _sse(event)

    return EventSourceResponse(event_generator(), headers=_SSE_HEADERS)
