"""Auth routes — verify the Supabase JWT and return the user."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, get_current_user
from app.api.schemas import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser = Depends(get_current_user)) -> UserResponse:
    """Return the authenticated user (validates the bearer token)."""
    return UserResponse(user_id=user.user_id, email=user.email)
