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

from core.config import settings
from models.credit import CreditLedger
from models.user import User
from services.email_service import send_credit_reset_notification

logger = structlog.get_logger()

# Plan daily limits — maps to plan_limits in config but enforced per-day
PLAN_DAILY_LIMITS: dict[str, int] = {
    "free":       2,    # 2 simulations per day (free LLM APIs have strict rate limits)
    "open":       2,    # Same as free during beta
    "pro":        10,   # 10 per day for pro users
    "enterprise": -1,   # Unlimited
}


async def reconcile_daily_credits(user_id: str, db: AsyncSession) -> tuple[User | None, bool, int]:
    """Return the locked user after applying any elapsed 24-hour reset."""
    result = await db.execute(
        select(User).where(User.id == user_id).with_for_update()
    )
    locked_user = result.scalar_one_or_none()
    if not locked_user:
        return None, False, 0

    now = datetime.now(timezone.utc)
    last_reset = locked_user.billing_period_start
    previous_usage = locked_user.simulations_this_month
    daily_limit = PLAN_DAILY_LIMITS.get(locked_user.plan_tier, 2)

    if daily_limit == -1:
        return locked_user, False, previous_usage

    if (now - last_reset).total_seconds() >= 86400:
        locked_user.simulations_this_month = 0
        locked_user.billing_period_start = now
        return locked_user, True, previous_usage

    return locked_user, False, previous_usage


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
    locked_user, _, _ = await reconcile_daily_credits(user.id, db)
    if not locked_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get daily limit for this user's plan
    daily_limit = PLAN_DAILY_LIMITS.get(locked_user.plan_tier, 2)

    if daily_limit != -1 and locked_user.simulations_this_month >= daily_limit:
        resets_at = (locked_user.billing_period_start + timedelta(days=1)).isoformat()
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


async def maybe_reset_daily_credits(user: User, db: AsyncSession) -> bool:
    """Reset an expired daily quota window and send the notification email once."""
    locked_user, reset_due, previous_usage = await reconcile_daily_credits(user.id, db)
    if not locked_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not reset_due:
        return False

    await db.commit()

    if previous_usage <= 0:
        return True

    daily_limit = PLAN_DAILY_LIMITS.get(locked_user.plan_tier, 2)
    await send_credit_reset_notification(
        to_email=locked_user.email,
        user_name=locked_user.full_name or locked_user.email.split("@")[0],
        daily_limit=daily_limit,
        reset_url=f"https://{settings.app_domain}/new",
    )
    return True


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
