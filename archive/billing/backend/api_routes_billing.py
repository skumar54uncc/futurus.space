# Archived from backend/api/routes/billing.py — do not import from here.

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from api.middleware.auth import get_current_user
from models.user import User
from schemas.billing import PlansResponse, PlanInfo, CheckoutRequest, CheckoutResponse, PortalResponse
from services.stripe_service import (
    create_checkout_session,
    create_portal_session,
    handle_checkout_completed,
    handle_subscription_updated,
    handle_subscription_deleted,
    handle_payment_failed,
)
from core.config import settings
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api/billing", tags=["billing"])

PLANS = [
    PlanInfo(
        name="Free", tier="free", price_monthly=0, agents=50, turns=20,
        sims_per_month=1, ensemble=1,
        features=["1 simulation", "50 agents", "Basic report", "Community support"],
    ),
    PlanInfo(
        name="Founder", tier="founder", price_monthly=49, agents=500, turns=40,
        sims_per_month=5, ensemble=1,
        features=["5 simulations/mo", "500 agents", "Full report", "Report chat", "PDF export"],
    ),
    PlanInfo(
        name="Studio", tier="studio", price_monthly=199, agents=1000, turns=60,
        sims_per_month=20, ensemble=3,
        features=["20 simulations/mo", "1,000 agents", "3x ensemble", "Investor reports", "Priority support"],
    ),
    PlanInfo(
        name="Enterprise", tier="enterprise", price_monthly=499, agents=2000, turns=80,
        sims_per_month=-1, ensemble=5,
        features=["Unlimited simulations", "2,000 agents", "5x ensemble", "Custom personas", "Dedicated support", "SSO"],
    ),
]


@router.get("/plans", response_model=PlansResponse)
async def get_plans(current_user: User = Depends(get_current_user)):
    return PlansResponse(plans=PLANS, current_tier=current_user.plan_tier)


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    url = await create_checkout_session(
        current_user, request.plan_tier, request.success_url, request.cancel_url
    )
    return CheckoutResponse(checkout_url=url)


@router.post("/portal", response_model=PortalResponse)
async def create_portal(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    url = await create_portal_session(current_user)
    return PortalResponse(portal_url=url)


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        await handle_checkout_completed(data, db)
    elif event_type == "customer.subscription.updated":
        await handle_subscription_updated(data, db)
    elif event_type == "customer.subscription.deleted":
        await handle_subscription_deleted(data, db)
    elif event_type == "invoice.payment_failed":
        await handle_payment_failed(data, db)
    else:
        logger.info("unhandled_webhook_event", event_type=event_type)

    return {"status": "ok"}
