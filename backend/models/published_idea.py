import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Float, JSON, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PublishedIdea(Base):
    __tablename__ = "published_ideas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("simulations.id", ondelete="CASCADE"), unique=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_avatar_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)

    # Agent voting scores per category (0-100)
    score_market_demand: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    score_retention: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    score_virality: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    score_feasibility: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    overall_rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Full breakdown stored as JSON for detail views
    score_breakdown: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
