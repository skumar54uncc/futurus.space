# Archived: credit_service previously incremented usage and supported CreditLedger / purchases.

"""Full credit management: check balances, deduct, add, reset monthly."""
import uuid
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.user import User
from models.credit import CreditLedger
import structlog

logger = structlog.get_logger()


async def check_and_deduct_credit(user: User, db: AsyncSession) -> None:
    user.simulations_this_month += 1
    await db.commit()
    return


async def add_credits(user_id: str, amount: int, db: AsyncSession, reason: str = "purchase") -> int:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.credit_balance += amount
    ledger = CreditLedger(
        id=uuid.uuid4(),
        user_id=user.id,
        amount=amount,
        balance_after=user.credit_balance,
        reason=reason,
    )
    db.add(ledger)
    await db.commit()
    logger.info("credits_added", user_id=user_id, amount=amount, balance=user.credit_balance)
    return user.credit_balance


async def reset_monthly_simulations(user_id: str, db: AsyncSession) -> None:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.simulations_this_month = 0
        user.billing_period_start = datetime.utcnow()
        await db.commit()
        logger.info("monthly_reset", user_id=user_id)
