"""Auth dependency tests (JWT validation + dev fallback)."""

from __future__ import annotations

import datetime as dt

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps import get_current_user
from app.config import Settings

_SECRET = "test-secret"


def _settings(secret=None):
    return Settings(supabase_jwt_secret=secret)


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_dev_mode_returns_dev_user_without_secret():
    user = get_current_user(credentials=None, settings=_settings(secret=None))
    assert user.user_id == "dev-user"


def test_missing_token_rejected_when_secret_set():
    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=None, settings=_settings(secret=_SECRET))
    assert exc.value.status_code == 401


def test_invalid_token_rejected():
    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=_creds("garbage"), settings=_settings(secret=_SECRET))
    assert exc.value.status_code == 401


def test_valid_token_accepted():
    token = jwt.encode(
        {
            "sub": "user-123",
            "email": "a@b.com",
            "aud": "authenticated",
            "exp": dt.datetime.now(dt.UTC) + dt.timedelta(hours=1),
        },
        _SECRET,
        algorithm="HS256",
    )
    user = get_current_user(credentials=_creds(token), settings=_settings(secret=_SECRET))
    assert user.user_id == "user-123"
    assert user.email == "a@b.com"
