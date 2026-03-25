"""
SECURITY: Credit and monthly simulation quota enforcement (row-locked, race-safe).
"""
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.credit import CreditLedger
from models.user import User

logger = structlog.get_logger()


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
    SECURITY: Atomic quota check with SELECT FOR UPDATE to prevent concurrent bypass.
    """
    result = await db.execute(
        select(User).where(User.id == user.id).with_for_update()
    )
    locked_user = result.scalar_one_or_none()
    if not locked_user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(timezone.utc)
    period_start = locked_user.billing_period_start
    if period_start.tzinfo is None:
        period_start = period_start.replace(tzinfo=timezone.utc)

    # SECURITY: Reset monthly counter each billing month
    if (now - period_start).days >= 30:
        locked_user.simulations_this_month = 0
        locked_user.billing_period_start = now

    limits = settings.plan_limits.get(
        locked_user.plan_tier, settings.plan_limits["free"]
    )
    monthly_limit = limits.get("sims_per_month", 1)

    if monthly_limit == -1:
        # Unlimited (enterprise) — still count usage
        locked_user.simulations_this_month += 1
        await db.commit()
        logger.info(
            "simulation_quota_unlimited_increment",
            user_id=user.id,
            sims_this_month=locked_user.simulations_this_month,
        )
        return

    if locked_user.simulations_this_month < monthly_limit:
        locked_user.simulations_this_month += 1
        await db.commit()
        logger.info(
            "simulation_quota_monthly_increment",
            user_id=user.id,
            sims_this_month=locked_user.simulations_this_month,
            monthly_limit=monthly_limit,
        )
        return

    if locked_user.credit_balance > 0:
        locked_user.credit_balance -= 1
        _record_ledger(
            db,
            locked_user.id,
            -1,
            locked_user.credit_balance,
            "one_off_credit_used",
        )
        await db.commit()
        logger.info(
            "credit_balance_deducted",
            user_id=user.id,
            credits_remaining=locked_user.credit_balance,
        )
        return

    raise HTTPException(
        status_code=402,
        detail={
            "error": "insufficient_credits",
            "message": f"You've reached your limit of {monthly_limit} simulations this month.",
            "upgrade_url": f"https://{settings.app_domain}/billing",
        },
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
