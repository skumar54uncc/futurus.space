import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    plan_tier: Mapped[str] = mapped_column(String(50), nullable=False, default="free")
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subscription_status: Mapped[str] = mapped_column(String(50), nullable=False, default="inactive")
    subscription_period_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    credit_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    simulations_this_month: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    billing_period_start: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    team_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
