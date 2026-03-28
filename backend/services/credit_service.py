"""
SECURITY: Daily simulation quota enforcement (row-locked, race-safe).
Per-plan daily limits. Resets every 24 hours.
"""
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.credit import CreditLedger
from models.user import User

logger = structlog.get_logger()

# Plan daily limits — maps to plan_limits in config but enforced per-day
PLAN_DAILY_LIMITS: dict[str, int] = {
    "free":       1,    # 1 simulation per day (free LLM APIs have strict rate limits)
    "open":       1,    # Same as free during beta
    "pro":        10,   # 10 per day for pro users
    "enterprise": -1,   # Unlimited
}


def _record_ledger(
    db: AsyncSession, user_id: str, amount: int, balance_after: int, reason: str
) -> None:
    # SECURITY: Immutable audit trail for credit movements
    entry = CreditLedger(
        id=uuid.uuid4(),
        user_id=user_id,
        amount=amount,
        balance_after=balance_after,
        reason=reason,
    )
    db.add(entry)


async def check_and_deduct_credit(user: User, db: AsyncSession) -> None:
    """
    Enforce per-day simulation limits based on plan tier.
    Uses SELECT FOR UPDATE to prevent race conditions.
    Raises HTTP 429 if daily limit reached.
    """
    result = await db.execute(
        select(User).where(User.id == user.id).with_for_update()
    )
    locked_user = result.scalar_one_or_none()
    if not locked_user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(timezone.utc)
    last_reset = locked_user.billing_period_start
    # billing_period_start is now always timezone-aware (DateTime(timezone=True))

    # Reset daily counter if it's been more than 24 hours
    if (now - last_reset).total_seconds() >= 86400:
        locked_user.simulations_this_month = 0   # "this_month" = daily counter (legacy name)
        locked_user.billing_period_start = now
        last_reset = now

    # Get daily limit for this user's plan
    daily_limit = PLAN_DAILY_LIMITS.get(locked_user.plan_tier, 2)

    if daily_limit != -1 and locked_user.simulations_this_month >= daily_limit:
        resets_at = (last_reset + timedelta(days=1)).isoformat()
        raise HTTPException(
            status_code=429,
            detail={
                "error": "daily_limit_reached",
                "message": (
                    f"You've used your {daily_limit} simulation(s) for today. "
                    "Since we use free-tier LLM APIs, we limit usage to keep things running for everyone. "
                    "Come back tomorrow!"
                ),
                "resets_at": resets_at,
                "plan": locked_user.plan_tier,
            },
        )

    locked_user.simulations_this_month += 1
    await db.commit()
    logger.info(
        "simulation_credit_deducted",
        user_id=user.id,
        plan=locked_user.plan_tier,
        used_today=locked_user.simulations_this_month,
        daily_limit=daily_limit,
    )


async def add_credits(user_id: str, amount: int, reason: str, db: AsyncSession) -> None:
    """Add credits (e.g. Stripe webhook)."""
    result = await db.execute(
        select(User).where(User.id == user_id).with_for_update()
    )
    u = result.scalar_one_or_none()
    if not u:
        return
    u.credit_balance += amount
    _record_ledger(db, user_id, amount, u.credit_balance, reason)
    await db.commit()


async def reset_monthly_simulations(user_id: str, db: AsyncSession) -> None:
    """Reset monthly counter (e.g. new billing period)."""
    result = await db.execute(
        select(User).where(User.id == user_id).with_for_update()
    )
    u = result.scalar_one_or_none()
    if not u:
        return
    u.simulations_this_month = 0
    u.billing_period_start = datetime.now(timezone.utc)
    await db.commit()
