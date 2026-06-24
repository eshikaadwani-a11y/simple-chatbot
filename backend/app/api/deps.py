"""Auth dependencies.

Protected endpoints depend on ``get_current_user`` which validates the Supabase
JWT (HS256, signed with the project's JWT secret) and returns the user identity.
In development, if no JWT secret is configured the dependency falls back to a
``dev`` user so the stack is runnable end-to-end without Supabase.
"""

from __future__ import annotations

import logging

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings

logger = logging.getLogger("learngraph")
_bearer = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(self, user_id: str, email: str | None = None):
        self.user_id = user_id
        self.email = email


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    # Dev fallback: with no JWT secret configured we cannot verify tokens, so we
    # run as an anonymous dev user. We ignore any supplied token rather than
    # attempting (and failing) to decode it with an empty key.
    if not settings.supabase_jwt_secret:
        return CurrentUser(user_id="dev-user", email="dev@example.com")

    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        logger.info("JWT validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject"
        )
    return CurrentUser(user_id=user_id, email=payload.get("email"))


def require_admin(
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    """Allow only configured admin emails.

    If ``ADMIN_EMAILS`` is unset, admin access is permitted only outside
    production (developer convenience); production requires an explicit allow-list.
    """
    admins = settings.admin_email_set
    if not admins:
        if settings.environment.lower() in ("production", "prod"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Admin not configured"
            )
        return user
    if (user.email or "").lower() not in admins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
