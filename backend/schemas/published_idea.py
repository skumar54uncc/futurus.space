import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PublishedIdeaResponse(BaseModel):
    id: uuid.UUID
    simulation_id: uuid.UUID
    user_name: str
    user_avatar_url: Optional[str] = None
    title: str
    description: str
    category: str
    score_market_demand: float
    score_retention: float
    score_virality: float
    score_feasibility: float
    overall_rating: float
    score_breakdown: dict
    agent_thinking: list[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


class PublishedIdeaListResponse(BaseModel):
    ideas: list[PublishedIdeaResponse]
    total: int
