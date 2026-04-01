import json
import threading
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth import get_current_user
from api.middleware.rate_limiter import LIMITS, limiter
from core.config import settings
from core.database import get_db
from models.simulation import Simulation, SimulationEvent, SimulationStatus
from models.user import User
from schemas.simulation import (
    AnalyzeIdeaRequest,
    PersonaGenerateRequest,
    RefineIdeaRequest,
    SimulationCreateRequest,
    SimulationResponse,
)
from services.credit_service import check_and_deduct_credit
from services.idea_analyzer import analyze_idea, refine_idea
from services.llm_router import AllProvidersExhausted
from services.persona_generator import generate_personas
from workers.simulation_worker import run_simulation, run_simulation_inline

logger = structlog.get_logger()
router = APIRouter(prefix="/api/simulations", tags=["simulations"])


def _run_inline_worker_safe(simulation_id: str) -> None:
    try:
        run_simulation_inline(simulation_id)
    except Exception:
        logger.exception("run_simulation_inline_crashed", simulation_id=simulation_id)


@router.post("/analyze-idea")
@limiter.limit(LIMITS["analyze_idea"])
async def analyze_idea_endpoint(
    request: Request,
    body: AnalyzeIdeaRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        return await analyze_idea(body.raw_idea)
    except AllProvidersExhausted as exc:
        logger.warning("analyze_idea_llm_exhausted", detail=str(exc))
        raise HTTPException(
            status_code=503,
            detail="Analysis is temporarily unavailable. Check LLM API keys and quotas, then try again.",
        ) from exc
    except json.JSONDecodeError as exc:
        logger.warning("analyze_idea_invalid_json", error=str(exc))
        raise HTTPException(
            status_code=502,
            detail="The analysis model returned invalid data. Please try again.",
        ) from exc


@router.post("/refine-idea")
@limiter.limit(LIMITS["refine_idea"])
async def refine_idea_endpoint(
    request: Request,
    body: RefineIdeaRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        return await refine_idea(
            body.raw_idea,
            [a.model_dump() for a in body.answers],
        )
    except AllProvidersExhausted as exc:
        logger.warning("refine_idea_llm_exhausted", detail=str(exc))
        raise HTTPException(
            status_code=503,
            detail="Refinement is temporarily unavailable. Check LLM API keys and quotas, then try again.",
        ) from exc
    except json.JSONDecodeError as exc:
        logger.warning("refine_idea_invalid_json", error=str(exc))
        raise HTTPException(
            status_code=502,
            detail="The analysis model returned invalid data. Please try again.",
        ) from exc


@router.post("/", response_model=SimulationResponse)
@limiter.limit(LIMITS["simulation_create"])
async def create_simulation(
    request: Request,
    payload: SimulationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    idempotency_key = request.headers.get("X-Idempotency-Key", "").strip()
    if idempotency_key:
        try:
            from core.redis import get_redis

            r = await get_redis()
            cache_key = f"idem:{current_user.id}:{idempotency_key}"
            cached_sim_id = await r.get(cache_key)
            if cached_sim_id:
                sim_uuid = uuid.UUID(
                    cached_sim_id
                    if isinstance(cached_sim_id, str)
                    else str(cached_sim_id)
                )
                result = await db.execute(
                    select(Simulation).where(Simulation.id == sim_uuid)
                )
                existing = result.scalar_one_or_none()
                if existing:
                    logger.info(
                        "idempotent_simulation_returned",
                        sim_id=str(sim_uuid),
                    )
                    return SimulationResponse.model_validate(existing)
        except Exception as e:
            logger.warning("idempotency_check_failed", error=str(e))

    await check_and_deduct_credit(current_user, db)
    limits = settings.simulation_limits
    effective_agents = min(payload.agent_count, limits["agents"])
    effective_turns = min(payload.max_turns, limits["turns"])
    personas_data = [p.model_dump() for p in payload.personas] if payload.personas else []
    if len(personas_data) > effective_agents:
        personas_data = personas_data[:effective_agents]

    sim = Simulation(
        id=uuid.uuid4(),
        user_id=current_user.id,
        business_name=payload.business_name,
        idea_description=payload.idea_description,
        target_market=payload.target_market,
        pricing_model=payload.pricing_model,
        price_points=payload.price_points,
        gtm_channels=payload.gtm_channels,
        competitors=[c.model_dump() for c in payload.competitors],
        key_assumptions=[a.model_dump() for a in payload.key_assumptions],
        vertical=payload.vertical,
        personas=personas_data,
        agent_count=effective_agents,
        max_turns=effective_turns,
        ensemble_runs=limits["ensemble"],
        plan_tier=current_user.plan_tier,
        status=SimulationStatus.QUEUED,
    )
    db.add(sim)
    await db.commit()
    await db.refresh(sim)

    if settings.simulation_worker_inline:
        threading.Thread(
            target=_run_inline_worker_safe,
            args=(str(sim.id),),
            daemon=True,
        ).start()
    else:
        try:
            task = run_simulation.delay(str(sim.id))
            sim.celery_task_id = task.id
            await db.commit()
        except Exception as e:
            logger.warning(
                "celery_enqueue_failed_running_inline",
                simulation_id=str(sim.id),
                error=str(e),
            )
            sim.celery_task_id = None
            await db.commit()
            threading.Thread(
                target=_run_inline_worker_safe,
                args=(str(sim.id),),
                daemon=True,
            ).start()

    if idempotency_key:
        try:
            from core.redis import get_redis

            r = await get_redis()
            await r.set(
                f"idem:{current_user.id}:{idempotency_key}",
                str(sim.id),
                ex=86400,
            )
        except Exception:
            pass

    return SimulationResponse.model_validate(sim)


@router.get("/", response_model=list[SimulationResponse])
@limiter.limit(LIMITS["default_authenticated"])
async def list_simulations(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Simulation)
        .where(Simulation.user_id == current_user.id)
        .order_by(Simulation.created_at.desc())
        .limit(50)
    )
    return [SimulationResponse.model_validate(s) for s in result.scalars()]


@router.post("/{simulation_id}/revoke", response_model=SimulationResponse)
@limiter.limit(LIMITS["default_authenticated"])
async def revoke_simulation(
    request: Request,
    simulation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from services.simulation_delete import revoke_simulation_for_user

    sim, err = await revoke_simulation_for_user(db, simulation_id, current_user.id)
    if err == "not_found":
        raise HTTPException(status_code=404, detail="Simulation not found")
    if err == "not_revokable":
        raise HTTPException(
            status_code=400,
            detail="This simulation is not queued or in progress, so there is nothing to revoke.",
        )
    return SimulationResponse.model_validate(sim)


@router.get("/{simulation_id}/events")
@limiter.limit(LIMITS["default_authenticated"])
async def get_simulation_events(
    request: Request,
    simulation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(80, ge=1, le=200),
):
    own = await db.execute(
        select(Simulation.id).where(
            Simulation.id == simulation_id,
            Simulation.user_id == current_user.id,
        )
    )
    if own.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Simulation not found")

    ev = await db.execute(
        select(SimulationEvent)
        .where(SimulationEvent.simulation_id == simulation_id)
        .order_by(desc(SimulationEvent.id))
        .limit(limit)
    )
    rows = ev.scalars().all()
    return [
        {
            "id": e.id,
            "turn": e.turn,
            "agent_name": e.agent_name,
            "segment": e.agent_segment,
            "event_type": e.event_type,
            "description": e.event_description,
        }
        for e in rows
    ]


@router.get("/{simulation_id}", response_model=SimulationResponse)
@limiter.limit(LIMITS["default_authenticated"])
async def get_simulation(
    request: Request,
    simulation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Simulation).where(
            Simulation.id == simulation_id,
            Simulation.user_id == current_user.id,
        )
    )
    sim = result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return SimulationResponse.model_validate(sim)


@router.delete("/{simulation_id}")
@limiter.limit(LIMITS["default_authenticated"])
async def delete_simulation(
    request: Request,
    simulation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from services.simulation_delete import delete_simulation_for_user

    deleted = await delete_simulation_for_user(db, simulation_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return JSONResponse({"ok": True})


@router.post("/{simulation_id}/notify", response_model=SimulationResponse)
@limiter.limit(LIMITS["default_authenticated"])
async def toggle_notify(
    request: Request,
    simulation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Simulation).where(
            Simulation.id == simulation_id,
            Simulation.user_id == current_user.id,
        )
    )
    sim = result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    if sim.status not in (SimulationStatus.QUEUED, SimulationStatus.BUILDING_SEED, SimulationStatus.GENERATING_PERSONAS, SimulationStatus.RUNNING, SimulationStatus.GENERATING_REPORT):
        raise HTTPException(status_code=400, detail="Simulation is already finished")
    sim.notify_on_complete = not sim.notify_on_complete
    await db.commit()
    await db.refresh(sim)
    return SimulationResponse.model_validate(sim)


@router.post("/{simulation_id}/rerun", response_model=SimulationResponse)
@limiter.limit(LIMITS["simulation_create"])
async def rerun_simulation(
    request: Request,
    simulation_id: uuid.UUID,
    payload: SimulationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_simulation(request, payload, db, current_user)


@router.post("/generate-personas")
@limiter.limit(LIMITS["generate_personas"])
async def generate_personas_endpoint(
    request: Request,
    body: PersonaGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    limits = settings.simulation_limits
    count = min(body.agent_count, limits["agents"])
    personas = await generate_personas(
        body.vertical,
        body.target_market,
        body.idea_description,
        count,
    )
    return personas
