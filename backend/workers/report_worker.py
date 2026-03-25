"""Report generation Celery task — can be triggered independently to regenerate reports."""
import asyncio
from workers.celery_app import celery_app
from celery import Task
import structlog

logger = structlog.get_logger()


class ReportTask(Task):
    abstract = True
    max_retries = 3
    default_retry_delay = 15


@celery_app.task(bind=True, base=ReportTask, name="generate_report")
def generate_report_task(self, simulation_id: str):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_generate_report_async(simulation_id))
    finally:
        loop.close()


async def _generate_report_async(simulation_id: str):
    from core.database import AsyncSessionLocal
    from models.simulation import Simulation, SimulationEvent
    from services.report_generator import generate_report
    from sqlalchemy import select
    import uuid

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Simulation).where(Simulation.id == uuid.UUID(simulation_id))
        )
        sim = result.scalar_one_or_none()
        if not sim:
            logger.error("simulation_not_found", simulation_id=simulation_id)
            return

        events_result = await db.execute(
            select(SimulationEvent)
            .where(SimulationEvent.simulation_id == sim.id)
            .order_by(SimulationEvent.turn)
        )
        events = list(events_result.scalars())

        report = await generate_report(sim, events, db)
        logger.info("report_regenerated", simulation_id=simulation_id, report_id=str(report.id))
