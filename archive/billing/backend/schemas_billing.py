# Archived from backend/schemas/billing.py

from pydantic import BaseModel
from typing import Optional


class PlanInfo(BaseModel):
    name: str
    tier: str
    price_monthly: float
    agents: int
    turns: int
    sims_per_month: int
    ensemble: int
    features: list[str]


class PlansResponse(BaseModel):
    plans: list[PlanInfo]
    current_tier: str


class CheckoutRequest(BaseModel):
    plan_tier: str
    success_url: str = "http://localhost:3000/billing?success=true"
    cancel_url: str = "http://localhost:3000/billing?canceled=true"


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


class CreditPurchaseRequest(BaseModel):
    amount: int
