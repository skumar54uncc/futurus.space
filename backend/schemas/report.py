import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from schemas.simulation import MAX_HISTORY_MESSAGES, MAX_HISTORY_MSG_LEN, MAX_MESSAGE_LENGTH


class SummaryMetrics(BaseModel):
    adoption_rate: float
    churn_rate: float
    viral_coefficient: float
    total_adopters: int
    total_churned: int
    simulation_turns: int = 0
    agent_count: int = 0
    confidence_score: float


class AdoptionPoint(BaseModel):
    turn: int
    month_equivalent: float
    adopters: int
    churned: int
    net: int
    cumulative: int


class PersonaResult(BaseModel):
    segment: str
    adoption_rate: float
    churn_rate: float
    referrals_generated: int = 0


class FailureEvent(BaseModel):
    turn: int
    month_equivalent: float
    event: str
    impact_level: str
    affected_segment: str


class Risk(BaseModel):
    risk: str
    probability: str
    impact: str
    mitigation: str


class PivotSuggestion(BaseModel):
    pivot: str
    rationale: str
    confidence: str
    evidence_from_simulation: str


class KeyInsight(BaseModel):
    insight: str
    supporting_evidence: str
    actionability: str


class Citation(BaseModel):
    id: int
    title: str = ""
    text: str
    source: str
    url: str
    year: Optional[int] = None


class ReportResponse(BaseModel):
    id: uuid.UUID
    simulation_id: uuid.UUID
    summary_metrics: dict
    adoption_curve: list
    persona_breakdown: list
    failure_timeline: list
    risk_matrix: list
    pivot_suggestions: list
    key_insights: list
    viability_summary: Optional[dict] = None
    ensemble_variance: Optional[dict] = None
    citations: list[dict] = []
    pdf_url: Optional[str] = None
    investor_pdf_url: Optional[str] = None
    share_token: Optional[str] = None
    created_at: datetime
    # Populated for public share links only (joined simulation headline)
    business_name: Optional[str] = None
    idea_description: Optional[str] = None

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    # SECURITY: Bounded chat payload for LLM cost and injection surface
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)
    history: list[dict] = Field(default_factory=list, max_length=MAX_HISTORY_MESSAGES)

    @field_validator("history")
    @classmethod
    def validate_history(cls, v: list) -> list[dict]:
        sanitized: list[dict] = []
        for msg in v[-MAX_HISTORY_MESSAGES:]:
            if isinstance(msg, dict):
                role = str(msg.get("role", "user"))[:16]
                content = str(msg.get("content", ""))[:MAX_HISTORY_MSG_LEN]
                sanitized.append({"role": role, "content": content})
        return sanitized


class ChatResponse(BaseModel):
    response: str
