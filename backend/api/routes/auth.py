from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth import get_current_user
from api.middleware.rate_limiter import LIMITS, limiter
from core.database import get_db
from models.user import User
from schemas.user import UserResponse, UserUpdateRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
@limiter.limit(LIMITS["default_authenticated"])
async def get_me(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
@limiter.limit(LIMITS["default_authenticated"])
async def update_me(
    request: Request,
    updates: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if updates.full_name is not None:
        current_user.full_name = updates.full_name
    if updates.onboarding_completed is not None:
        current_user.onboarding_completed = updates.onboarding_completed
    if updates.preferences is not None:
        current_user.preferences = updates.preferences
    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)
