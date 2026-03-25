"""Revoke Celery work and remove simulation rows (events + report + simulation)."""
import uuid

import structlog
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.simulation import Simulation, SimulationEvent, Report, SimulationStatus
from workers.celery_app import celery_app

logger = structlog.get_logger()

STOPPED_BY_USER_MESSAGE = "Stopped by user"

_REVOKABLE = frozenset(
    {
        SimulationStatus.QUEUED,
        SimulationStatus.BUILDING_SEED,
        SimulationStatus.GENERATING_PERSONAS,
        SimulationStatus.RUNNING,
        SimulationStatus.GENERATING_REPORT,
    }
)


def revoke_simulation_celery_task(task_id: str | None) -> None:
    if not task_id:
        return
    try:
        # terminate=False: on Windows solo pool, terminate=True can kill the whole worker process.
        # Queued tasks are removed; running tasks stop at the next DB poll in simulation_worker.
        celery_app.control.revoke(task_id, terminate=False)
    except Exception as e:
        logger.warning("celery_revoke_failed", task_id=task_id, error=str(e))


async def revoke_simulation_for_user(
    db: AsyncSession,
    simulation_id: uuid.UUID,
    user_id: str,
) -> tuple[Simulation | None, str | None]:
    """
    Stop a queued or in-flight run without deleting data.
    Returns (simulation, None) on success, (None, "not_found") or (None, "not_revokable").
    """
    result = await db.execute(
        select(Simulation).where(
            Simulation.id == simulation_id,
            Simulation.user_id == user_id,
        )
    )
    sim = result.scalar_one_or_none()
    if not sim:
        return None, "not_found"
    if sim.status not in _REVOKABLE:
        return None, "not_revokable"

    sim.status = SimulationStatus.FAILED
    sim.error_message = STOPPED_BY_USER_MESSAGE
    revoke_simulation_celery_task(sim.celery_task_id)
    await db.commit()
    await db.refresh(sim)
    logger.info("simulation_revoked", simulation_id=str(simulation_id), user_id=user_id)
    return sim, None


async def delete_simulation_for_user(
    db: AsyncSession,
    simulation_id: uuid.UUID,
    user_id: str,
) -> bool:
    """
    Returns True if a row was deleted.
    Revokes Celery task if present, then deletes events, report, simulation.
    """
    result = await db.execute(
        select(Simulation).where(
            Simulation.id == simulation_id,
            Simulation.user_id == user_id,
        )
    )
    sim = result.scalar_one_or_none()
    if not sim:
        return False

    task_id = sim.celery_task_id
    db.expunge(sim)

    revoke_simulation_celery_task(task_id)

    try:
        await db.execute(delete(SimulationEvent).where(SimulationEvent.simulation_id == simulation_id))
        await db.execute(delete(Report).where(Report.simulation_id == simulation_id))
        await db.execute(
            delete(Simulation).where(
                Simulation.id == simulation_id,
                Simulation.user_id == user_id,
            )
        )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        logger.exception(
            "simulation_delete_integrity_error",
            simulation_id=str(simulation_id),
            user_id=user_id,
        )
        raise

    logger.info("simulation_deleted", simulation_id=str(simulation_id), user_id=user_id)
    return True
