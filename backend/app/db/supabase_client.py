"""Supabase client factory (service-role, backend only).

The service-role key bypasses Row-Level Security, so this client must NEVER be
exposed to the browser. The frontend uses the anon key + user JWT instead.
"""
from __future__ import annotations

import functools

from app.config import get_settings


@functools.lru_cache
def get_supabase():
    """Return a cached service-role Supabase client, or None if unconfigured."""
    settings = get_settings()
    if not settings.has_supabase:
        return None
    from supabase import create_client

    return create_client(settings.supabase_url, settings.supabase_service_role_key)
