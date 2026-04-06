import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth import get_current_user
from api.middleware.rate_limiter import LIMITS, limiter
from core.database import get_db
from models.published_idea import PublishedIdea
from models.simulation import Report, Simulation, SimulationStatus
from models.user import User
from schemas.published_idea import PublishedIdeaListResponse, PublishedIdeaResponse
from services.idea_rating import compute_idea_scores, vertical_to_category

logger = structlog.get_logger()
router = APIRouter(prefix="/api/ideas", tags=["ideas"])


def _extract_agent_thinking(report: Report | None) -> list[str]:
    if report is None or not isinstance(report.key_insights, list):
        return []
    thoughts: list[str] = []
    for item in report.key_insights[:3]:
        if isinstance(item, dict):
            text = str(item.get("insight") or "").strip()
            if text:
                thoughts.append(text)
        elif isinstance(item, str) and item.strip():
            thoughts.append(item.strip())
    return thoughts


@router.post("/{simulation_id}/publish", response_model=PublishedIdeaResponse)
@limiter.limit(LIMITS["default_authenticated"])
async def publish_idea(
    request: Request,
    simulation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Publish a completed simulation's idea to the public dashboard."""
    # Check if already published
    existing = await db.execute(
        select(PublishedIdea).where(PublishedIdea.simulation_id == simulation_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="This idea is already published")

    # Verify simulation ownership and completion
    sim_result = await db.execute(
        select(Simulation).where(
            Simulation.id == simulation_id,
            Simulation.user_id == current_user.id,
        )
    )
    sim = sim_result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    if sim.status != SimulationStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Simulation is not completed yet")

    # Get the report for scoring
    report_result = await db.execute(
        select(Report).where(Report.simulation_id == simulation_id)
    )
    report = report_result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=400, detail="No report found for this simulation")

    # Compute agent voting scores
    scores = compute_idea_scores(report.summary_metrics)

    idea = PublishedIdea(
        simulation_id=simulation_id,
        user_id=current_user.id,
        user_name=current_user.full_name or current_user.email.split("@")[0],
        user_avatar_url=current_user.avatar_url,
        title=sim.business_name,
        description=sim.idea_description,
        category=vertical_to_category(sim.vertical),
        score_market_demand=scores["market_demand"],
        score_retention=scores["retention"],
        score_virality=scores["virality"],
        score_feasibility=scores["feasibility"],
        overall_rating=scores["overall"],
        score_breakdown=scores["breakdown"],
    )
    db.add(idea)
    await db.commit()
    await db.refresh(idea)

    logger.info(
        "idea_published",
        idea_id=str(idea.id),
        simulation_id=str(simulation_id),
        user_id=current_user.id,
    )
    return PublishedIdeaResponse.model_validate(idea).model_copy(
        update={"agent_thinking": _extract_agent_thinking(report)}
    )


@router.delete("/{simulation_id}/unpublish")
@limiter.limit(LIMITS["default_authenticated"])
async def unpublish_idea(
    request: Request,
    simulation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a published idea (only by the owner)."""
    result = await db.execute(
        select(PublishedIdea).where(
            PublishedIdea.simulation_id == simulation_id,
            PublishedIdea.user_id == current_user.id,
        )
    )
    idea = result.scalar_one_or_none()
    if not idea:
        raise HTTPException(status_code=404, detail="Published idea not found")

    await db.delete(idea)
    await db.commit()
    return {"ok": True}


@router.get("/{simulation_id}/status")
@limiter.limit(LIMITS["default_authenticated"])
async def get_publish_status(
    request: Request,
    simulation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check if a simulation has been published."""
    result = await db.execute(
        select(PublishedIdea.id).where(
            PublishedIdea.simulation_id == simulation_id,
            PublishedIdea.user_id == current_user.id,
        )
    )
    return {"published": result.scalar_one_or_none() is not None}


@router.get("/", response_model=PublishedIdeaListResponse)
@limiter.limit(LIMITS["public"])
async def list_ideas(
    request: Request,
    db: AsyncSession = Depends(get_db),
    category: Optional[str] = Query(None, max_length=100),
    sort: str = Query("latest", pattern="^(latest|rating)$"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Public endpoint — list all published ideas with filters."""
    query = select(PublishedIdea).where(PublishedIdea.is_active == True)

    if category:
        query = query.where(PublishedIdea.category == category)

    if sort == "rating":
        query = query.order_by(desc(PublishedIdea.overall_rating))
    else:
        query = query.order_by(desc(PublishedIdea.created_at))

    # Count total
    count_query = select(func.count()).select_from(
        query.subquery()
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    rows = list(result.scalars())

    sim_ids = [r.simulation_id for r in rows]
    report_by_sim: dict[uuid.UUID, Report] = {}
    if sim_ids:
        reports_result = await db.execute(
            select(Report).where(Report.simulation_id.in_(sim_ids))
        )
        report_by_sim = {r.simulation_id: r for r in reports_result.scalars()}

    ideas = [
        PublishedIdeaResponse.model_validate(i).model_copy(
            update={"agent_thinking": _extract_agent_thinking(report_by_sim.get(i.simulation_id))}
        )
        for i in rows
    ]

    return PublishedIdeaListResponse(ideas=ideas, total=total)
