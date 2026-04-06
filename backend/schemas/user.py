from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    plan_tier: str
    credit_balance: int
    simulations_this_month: int
    daily_limit: int = 2
    billing_period_start: datetime
    subscription_status: str
    onboarding_completed: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    onboarding_completed: Optional[bool] = None
    preferences: Optional[dict] = None
