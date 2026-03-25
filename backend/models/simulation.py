import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, JSON, ForeignKey, Enum, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base
import enum


class SimulationStatus(str, enum.Enum):
    QUEUED = "queued"
    BUILDING_SEED = "building_seed"
    GENERATING_PERSONAS = "generating_personas"
    RUNNING = "running"
    GENERATING_REPORT = "generating_report"
    COMPLETED = "completed"
    FAILED = "failed"


class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    team_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    idea_description: Mapped[str] = mapped_column(Text, nullable=False)
    target_market: Mapped[str] = mapped_column(Text, nullable=False)
    pricing_model: Mapped[str] = mapped_column(String(100), nullable=False)
    price_points: Mapped[dict] = mapped_column(JSON, nullable=False)
    gtm_channels: Mapped[list] = mapped_column(JSON, nullable=False)
    competitors: Mapped[list] = mapped_column(JSON, nullable=False)
    key_assumptions: Mapped[list] = mapped_column(JSON, nullable=False)
    vertical: Mapped[str] = mapped_column(String(100), nullable=False)

    personas: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    agent_count: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    max_turns: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    ensemble_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    plan_tier: Mapped[str] = mapped_column(String(50), nullable=False, default="open")

    status: Mapped[SimulationStatus] = mapped_column(
        Enum(SimulationStatus), nullable=False, default=SimulationStatus.QUEUED
    )
    current_turn: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    agents_active: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    report: Mapped["Report"] = relationship("Report", back_populates="simulation", uselist=False)
    events: Mapped[list["SimulationEvent"]] = relationship("SimulationEvent", back_populates="simulation")


class SimulationEvent(Base):
    __tablename__ = "simulation_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    simulation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("simulations.id"))
    turn: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_segment: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_description: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    simulation: Mapped["Simulation"] = relationship("Simulation", back_populates="events")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("simulations.id"), unique=True)

    summary_metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    adoption_curve: Mapped[list] = mapped_column(JSON, nullable=False)
    persona_breakdown: Mapped[list] = mapped_column(JSON, nullable=False)
    failure_timeline: Mapped[list] = mapped_column(JSON, nullable=False)
    risk_matrix: Mapped[list] = mapped_column(JSON, nullable=False)
    pivot_suggestions: Mapped[list] = mapped_column(JSON, nullable=False)
    key_insights: Mapped[list] = mapped_column(JSON, nullable=False)

    ensemble_variance: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    pdf_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    investor_pdf_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    share_token: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    simulation: Mapped["Simulation"] = relationship("Simulation", back_populates="report")
