"""Orchestrates the full simulation lifecycle — from wizard input to queued Celery task."""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.simulation import Simulation, SimulationStatus
from models.user import User
from schemas.simulation import SimulationCreateRequest
from services.credit_service import check_and_deduct_credit
from workers.simulation_worker import run_simulation
from core.config import settings
import structlog

logger = structlog.get_logger()


async def create_simulation(
    request: SimulationCreateRequest,
    user: User,
    db: AsyncSession,
) -> Simulation:
    await check_and_deduct_credit(user, db)

    limits = settings.simulation_limits
    effective_agents = min(request.agent_count, limits["agents"])
    effective_turns = min(request.max_turns, limits["turns"])
    personas_data = [p.model_dump() for p in request.personas] if request.personas else []
    if len(personas_data) > effective_agents:
        personas_data = personas_data[:effective_agents]

    sim = Simulation(
        id=uuid.uuid4(),
        user_id=user.id,
        business_name=request.business_name,
        idea_description=request.idea_description,
        target_market=request.target_market,
        pricing_model=request.pricing_model,
        price_points=request.price_points,
        gtm_channels=request.gtm_channels,
        competitors=[c.model_dump() for c in request.competitors],
        key_assumptions=[a.model_dump() for a in request.key_assumptions],
        vertical=request.vertical,
        personas=personas_data,
        agent_count=effective_agents,
        max_turns=effective_turns,
        ensemble_runs=limits["ensemble"],
        plan_tier="open",
        status=SimulationStatus.QUEUED,
    )
    db.add(sim)
    await db.commit()
    await db.refresh(sim)

    import threading

    if settings.simulation_worker_inline:
        from workers.simulation_worker import run_simulation_inline

        threading.Thread(
            target=run_simulation_inline,
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
            from workers.simulation_worker import run_simulation_inline

            sim.celery_task_id = None
            await db.commit()
            threading.Thread(
                target=run_simulation_inline,
                args=(str(sim.id),),
                daemon=True,
            ).start()
            logger.info("simulation_created", simulation_id=str(sim.id), user_id=user.id)
            return sim

    logger.info("simulation_created", simulation_id=str(sim.id), user_id=user.id)
    return sim


async def get_user_simulations(user_id: str, db: AsyncSession, limit: int = 50) -> list[Simulation]:
    result = await db.execute(
        select(Simulation)
        .where(Simulation.user_id == user_id)
        .order_by(Simulation.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars())


async def get_simulation(simulation_id: uuid.UUID, user_id: str, db: AsyncSession) -> Simulation | None:
    result = await db.execute(
        select(Simulation).where(
            Simulation.id == simulation_id,
            Simulation.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()
