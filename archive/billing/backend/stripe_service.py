# Archived from backend/services/stripe_service.py — see archive/billing/README.md

"""Stripe subscription + webhook handling."""
import stripe
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.user import User
from services.credit_service import reset_monthly_simulations
from core.config import settings
import structlog

logger = structlog.get_logger()

PLAN_PRICE_MAP = {
    "founder": settings.stripe_price_founder,
    "studio": settings.stripe_price_studio,
    "enterprise": settings.stripe_price_enterprise,
}

PRICE_PLAN_MAP = {v: k for k, v in PLAN_PRICE_MAP.items() if v}


async def create_checkout_session(
    user: User, plan_tier: str, success_url: str, cancel_url: str
) -> str:
    if plan_tier not in PLAN_PRICE_MAP:
        raise HTTPException(status_code=400, detail=f"Invalid plan tier: {plan_tier}")

    price_id = PLAN_PRICE_MAP[plan_tier]
    if not price_id or price_id.startswith("price_..."):
        raise HTTPException(status_code=400, detail="Stripe prices not configured")

    if not user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"user_id": user.id},
        )
        user.stripe_customer_id = customer.id

    session = stripe.checkout.Session.create(
        customer=user.stripe_customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": user.id, "plan_tier": plan_tier},
    )
    return session.url


async def create_portal_session(user: User) -> str:
    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account found")

    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{settings.backend_url.replace(':8000', ':3000')}/billing",
    )
    return session.url


async def handle_checkout_completed(session_data: dict, db: AsyncSession) -> None:
    user_id = session_data.get("metadata", {}).get("user_id")
    plan_tier = session_data.get("metadata", {}).get("plan_tier", "founder")
    subscription_id = session_data.get("subscription")
    customer_id = session_data.get("customer")

    if not user_id:
        logger.warning("checkout_no_user_id", session=session_data.get("id"))
        return

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return

    user.plan_tier = plan_tier
    user.stripe_customer_id = customer_id
    user.stripe_subscription_id = subscription_id
    user.subscription_status = "active"
    await db.commit()
    logger.info("subscription_activated", user_id=user_id, plan=plan_tier)


async def handle_subscription_updated(subscription_data: dict, db: AsyncSession) -> None:
    subscription_id = subscription_data.get("id")
    status = subscription_data.get("status")
    price_id = (
        subscription_data.get("items", {})
        .get("data", [{}])[0]
        .get("price", {})
        .get("id", "")
    )
    plan_tier = PRICE_PLAN_MAP.get(price_id, "founder")

    result = await db.execute(
        select(User).where(User.stripe_subscription_id == subscription_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    user.subscription_status = status
    user.plan_tier = plan_tier if status == "active" else "free"
    await db.commit()

    if status == "active":
        await reset_monthly_simulations(user.id, db)

    logger.info("subscription_updated", user_id=user.id, status=status, plan=plan_tier)


async def handle_subscription_deleted(subscription_data: dict, db: AsyncSession) -> None:
    subscription_id = subscription_data.get("id")
    result = await db.execute(
        select(User).where(User.stripe_subscription_id == subscription_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    user.plan_tier = "free"
    user.subscription_status = "canceled"
    user.stripe_subscription_id = None
    await db.commit()
    logger.info("subscription_canceled", user_id=user.id)


async def handle_payment_failed(invoice_data: dict, db: AsyncSession) -> None:
    customer_id = invoice_data.get("customer")
    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    user.subscription_status = "past_due"
    await db.commit()
    logger.warning("payment_failed", user_id=user.id)
