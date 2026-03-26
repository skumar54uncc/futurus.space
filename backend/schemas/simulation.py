import re
import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# SECURITY: Cap LLM input sizes (cost + prompt-injection surface)
MAX_IDEA_LENGTH = 2000
MAX_MESSAGE_LENGTH = 1000
MAX_HISTORY_MESSAGES = 20
MAX_HISTORY_MSG_LEN = 500
MAX_Q_LEN = 300
MAX_A_LEN = 500
MAX_REFINE_QA = 10

_VALID_VERTICALS = frozenset(
    {"saas", "consumer_app", "marketplace", "physical_product", "service_business", "enterprise"}
)
_VALID_PRICING = frozenset({"freemium", "subscription", "one-time", "usage", "hybrid"})


class CompetitorInput(BaseModel):
    name: str
    url: str = ""
    description: str = ""


class AssumptionInput(BaseModel):
    variable: str
    value: str


class PersonaInput(BaseModel):
    name: str
    segment: str
    personality: list[str] = []
    budget_sensitivity: float = 0.5
    influence_score: float = 0.3
    decision_speed: str = "medium"
    main_motivation: str = ""
    main_objection: str = ""
    trigger_to_adopt: str = ""
    trigger_to_churn: str = ""


class SimulationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    business_name: str = Field(..., min_length=1, max_length=255)
    idea_description: str = Field(..., min_length=10, max_length=5000)
    target_market: str = Field(..., min_length=10, max_length=3000)
    pricing_model: str = Field(..., pattern="^(freemium|subscription|one-time|usage|hybrid)$")
    price_points: dict[str, float] = Field(..., min_length=1)
    gtm_channels: list[str] = Field(..., min_length=1)
    competitors: list[CompetitorInput] = Field(default_factory=list)
    key_assumptions: list[AssumptionInput] = Field(default_factory=list)
    vertical: str = Field(..., pattern="^(saas|consumer_app|marketplace|physical_product|service_business|enterprise)$")
    personas: list[PersonaInput] = Field(default_factory=list)
    agent_count: int = Field(default=50, ge=10, le=1000)
    max_turns: int = Field(default=20, ge=10, le=100)

    @field_validator("price_points", mode="before")
    @classmethod
    def coerce_price_points(cls, v: Any) -> dict[str, float]:
        if not v or not isinstance(v, dict):
            return {"basic": 0.0}
        out: dict[str, float] = {}
        for k, val in v.items():
            key = str(k).strip() or "tier"
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                out[key] = float(val)
            else:
                s = str(val).strip().replace(",", "")
                for sym in ("$", "€", "£", "₹", "¥"):
                    s = s.replace(sym, "")
                try:
                    out[key] = float(s)
                except ValueError:
                    out[key] = 0.0
        return out

    @field_validator("competitors", mode="before")
    @classmethod
    def coerce_competitors(cls, v: Any) -> list[dict]:
        if not v:
            return []
        if not isinstance(v, list):
            return []
        out: list[dict] = []
        for item in v:
            if isinstance(item, str) and item.strip():
                out.append({"name": item.strip(), "url": "", "description": ""})
            elif isinstance(item, dict):
                out.append(
                    {
                        "name": str(item.get("name") or "").strip() or "Unknown",
                        "url": str(item.get("url") or ""),
                        "description": str(item.get("description") or ""),
                    }
                )
        return out

    @field_validator("key_assumptions", mode="before")
    @classmethod
    def coerce_key_assumptions(cls, v: Any) -> list[dict]:
        if not v:
            return []
        if not isinstance(v, list):
            return []
        out: list[dict] = []
        for item in v:
            if isinstance(item, dict):
                out.append(
                    {
                        "variable": str(item.get("variable") or ""),
                        "value": "" if item.get("value") is None else str(item.get("value")),
                    }
                )
        return out

    @field_validator("vertical", mode="before")
    @classmethod
    def normalize_vertical(cls, v):
        if v is None:
            return "saas"
        s = str(v).strip().lower().replace(" ", "_").replace("-", "_")
        return s if s in _VALID_VERTICALS else "saas"

    @field_validator("pricing_model", mode="before")
    @classmethod
    def normalize_pricing_model(cls, v):
        if v is None:
            return "freemium"
        p = str(v).strip().lower().replace("_", "-")
        p = p.replace("one time", "one-time").replace("onetime", "one-time")
        return p if p in _VALID_PRICING else "freemium"


class SimulationResponse(BaseModel):
    id: uuid.UUID
    user_id: str
    business_name: str
    idea_description: str
    target_market: str
    pricing_model: str
    price_points: dict
    gtm_channels: list
    competitors: list
    key_assumptions: list
    vertical: str
    personas: list
    agent_count: int
    max_turns: int
    ensemble_runs: int
    plan_tier: str
    status: str
    current_turn: int
    agents_active: int
    estimated_cost_usd: float
    actual_cost_usd: float
    celery_task_id: Optional[str] = None
    error_message: Optional[str] = None
    notify_on_complete: bool = False
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PersonaGenerateRequest(BaseModel):
    # SECURITY: Tight bounds; route still clamps to simulation_limits["agents"]
    vertical: str = Field(..., max_length=100)
    target_market: str = Field(..., min_length=10, max_length=1000)
    idea_description: str = Field(..., min_length=10, max_length=MAX_IDEA_LENGTH)
    agent_count: int = Field(default=50, ge=10, le=500)


class AnalyzeIdeaRequest(BaseModel):
    raw_idea: str = Field(
        ...,
        min_length=10,
        max_length=MAX_IDEA_LENGTH,
        description="Raw idea text from user",
    )

    @field_validator("raw_idea")
    @classmethod
    def sanitize_idea(cls, v: str) -> str:
        # SECURITY: Block a few high-signal injection phrases (best-effort)
        injection_patterns = [
            r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
            r"disregard\s+.*instructions",
            r"you\s+are\s+now\s+(a|an|the)\s+",
            r"<\|.*\|>",
            r"\[INST\]",
        ]
        lower = v.lower()
        for pattern in injection_patterns:
            if re.search(pattern, lower):
                raise ValueError("Input contains disallowed patterns")
        return v.strip()


class QAItem(BaseModel):
    question: str = Field(..., max_length=MAX_Q_LEN)
    answer: str = Field(..., max_length=MAX_A_LEN)


class RefineIdeaRequest(BaseModel):
    raw_idea: str = Field(..., min_length=10, max_length=MAX_IDEA_LENGTH)
    answers: list[QAItem] = Field(..., max_length=MAX_REFINE_QA)

    @field_validator("answers")
    @classmethod
    def validate_qa_nonempty(cls, v: list[QAItem]) -> list[QAItem]:
        for item in v:
            if not item.question.strip() or not item.answer.strip():
                raise ValueError("Each question and answer must be non-empty")
        return v
