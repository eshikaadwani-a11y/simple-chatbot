"""Usage analytics, cost tracking, and LLM token accounting.

Everything here is best-effort and must never break a user request: failures are
swallowed and logged. When Supabase is configured, events go to the
``usage_events`` table; otherwise an in-memory list is used (dev/tests).
"""

from __future__ import annotations

import datetime as dt
import logging
from collections import Counter, defaultdict
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

from app.db.supabase_client import get_supabase

logger = logging.getLogger("learngraph")

# ---------------------------------------------------------------------------
# Cost model — USD per 1M tokens (prompt, completion).
# These are ESTIMATES; edit to match your provider's current pricing.
# Matched by prefix so versioned model ids (e.g. "gpt-5-2025-xx") still resolve.
# ---------------------------------------------------------------------------
PRICING_PER_MTOK: dict[str, tuple[float, float]] = {
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5": (1.25, 10.00),
    "claude": (3.00, 15.00),
    "gemini": (1.25, 10.00),
    "deepseek": (0.27, 1.10),
}


def estimate_cost(model: str | None, prompt_tokens: int, completion_tokens: int) -> float:
    if not model:
        return 0.0
    name = model.lower()
    rate = next((v for k, v in PRICING_PER_MTOK.items() if name.startswith(k) or k in name), None)
    if rate is None:
        return 0.0
    p_rate, c_rate = rate
    return round(prompt_tokens / 1e6 * p_rate + completion_tokens / 1e6 * c_rate, 6)


# ---------------------------------------------------------------------------
# In-memory fallback store
# ---------------------------------------------------------------------------
_EVENTS: list[dict[str, Any]] = []


def record_usage(
    *,
    user_id: str,
    event_type: str,
    agent: str | None = None,
    tool: str | None = None,
    model: str | None = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> None:
    """Persist a single usage event (best-effort)."""
    total = prompt_tokens + completion_tokens
    row = {
        "user_id": user_id,
        "event_type": event_type,
        "agent": agent,
        "tool": tool,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total,
        "cost_usd": estimate_cost(model, prompt_tokens, completion_tokens),
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
    }
    try:
        sb = get_supabase()
        if sb is None:
            _EVENTS.append(row)
        else:
            sb.table("usage_events").insert(row).execute()
    except Exception as exc:  # noqa: BLE001 - analytics must never break a request
        logger.warning("record_usage failed: %s", exc)


def record_run_usage(user_id: str, route: str | None, cb: TokenUsageCallback) -> None:
    """Record a completed agent run: one chat event + one event per tool used."""
    record_usage(
        user_id=user_id,
        event_type="chat",
        agent=route,
        model=cb.model,
        prompt_tokens=cb.prompt_tokens,
        completion_tokens=cb.completion_tokens,
    )
    for name in cb.tools_used:
        record_usage(user_id=user_id, event_type="tool", agent=route, tool=name)


# ---------------------------------------------------------------------------
# Token-usage callback
# ---------------------------------------------------------------------------
class TokenUsageCallback(BaseCallbackHandler):
    """Accumulates token usage, model name, and tool calls across one graph run."""

    def __init__(self) -> None:
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.model: str | None = None
        self.tools_used: list[str] = []

    def on_llm_end(self, response, **kwargs) -> None:  # noqa: ANN001
        try:
            usage = None
            output = getattr(response, "llm_output", None) or {}
            if isinstance(output, dict):
                usage = output.get("token_usage") or output.get("usage")
                self.model = output.get("model_name") or self.model
            # Fall back to message.usage_metadata (langchain_core >= 0.3).
            gens = getattr(response, "generations", None) or []
            if gens and gens[0]:
                msg = getattr(gens[0][0], "message", None)
                meta = getattr(msg, "usage_metadata", None)
                if meta:
                    self.prompt_tokens += int(meta.get("input_tokens", 0))
                    self.completion_tokens += int(meta.get("output_tokens", 0))
                    usage = None  # already counted
                rmeta = getattr(msg, "response_metadata", None) or {}
                self.model = rmeta.get("model_name") or self.model
            if usage:
                self.prompt_tokens += int(usage.get("prompt_tokens", 0))
                self.completion_tokens += int(usage.get("completion_tokens", 0))
        except Exception as exc:  # noqa: BLE001
            logger.debug("token usage parse failed: %s", exc)

    def on_tool_start(self, serialized, input_str, **kwargs) -> None:  # noqa: ANN001
        name = (serialized or {}).get("name") if isinstance(serialized, dict) else None
        if name:
            self.tools_used.append(name)


# ---------------------------------------------------------------------------
# Aggregation for the admin dashboard
# ---------------------------------------------------------------------------
def _load_events(limit: int = 10000) -> list[dict[str, Any]]:
    sb = get_supabase()
    if sb is None:
        return list(_EVENTS)
    try:
        res = (
            sb.table("usage_events")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("load events failed: %s", exc)
        return []


def _user_counts() -> tuple[int, int]:
    """Return (total_users, active_users_last_7_days)."""
    sb = get_supabase()
    cutoff = (dt.datetime.now(dt.UTC).date() - dt.timedelta(days=7)).isoformat()
    if sb is None:
        from app.memory.long_term import _MEM

        total = len(_MEM)
        active = sum(
            1 for v in _MEM.values() if (v.get("profile") or {}).get("last_active", "") >= cutoff
        )
        return total, active
    try:
        total = sb.table("learner_profiles").select("user_id", count="exact").execute().count or 0
        active = (
            sb.table("learner_profiles")
            .select("user_id", count="exact")
            .gte("last_active", cutoff)
            .execute()
            .count
            or 0
        )
        return total, active
    except Exception as exc:  # noqa: BLE001
        logger.warning("user counts failed: %s", exc)
        return 0, 0


def aggregate_admin() -> dict[str, Any]:
    """Compute the admin analytics summary from stored usage events."""
    events = _load_events()
    total_users, active_users = _user_counts()
    today = dt.datetime.now(dt.UTC).date().isoformat()
    month = today[:7]

    chat = [e for e in events if e.get("event_type") == "chat"]
    tools = [e for e in events if e.get("event_type") == "tool"]

    agent_counts = Counter(e.get("agent") or "unknown" for e in chat)
    tool_counts = Counter(e.get("tool") or "unknown" for e in tools)

    cost_total = round(sum(float(e.get("cost_usd") or 0) for e in events), 4)
    cost_today = round(
        sum(
            float(e.get("cost_usd") or 0)
            for e in events
            if str(e.get("created_at", "")).startswith(today)
        ),
        4,
    )
    cost_month = round(
        sum(
            float(e.get("cost_usd") or 0)
            for e in events
            if str(e.get("created_at", "")).startswith(month)
        ),
        4,
    )

    daily: dict[str, float] = defaultdict(float)
    for e in events:
        day = str(e.get("created_at", ""))[:10]
        if day:
            daily[day] += float(e.get("cost_usd") or 0)
    daily_series = [{"date": d, "cost": round(c, 4)} for d, c in sorted(daily.items())[-14:]]

    return {
        "total_users": total_users,
        "active_users_7d": active_users,
        "ai_requests": len(chat),
        "tool_calls": len(tools),
        "resume_analyses": sum(1 for e in events if e.get("event_type") == "resume_analysis"),
        "roadmaps_generated": agent_counts.get("roadmap", 0),
        "quiz_attempts": agent_counts.get("quiz", 0),
        "top_agents": agent_counts.most_common(6),
        "top_tools": tool_counts.most_common(8),
        "tokens_total": sum(int(e.get("total_tokens") or 0) for e in events),
        "cost_total_usd": cost_total,
        "cost_today_usd": cost_today,
        "cost_month_usd": cost_month,
        "daily_cost": daily_series,
    }
