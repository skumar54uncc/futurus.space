"""
The main Celery worker that runs the full simulation lifecycle.
This is a long-running task (5-20 min) — must be async-safe and retriable.
"""
import asyncio
import json
import sys
import uuid

import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_mirofish_path = os.environ.get("MIROFISH_PATH", "/mirofish")
if _mirofish_path and _mirofish_path not in sys.path:
    sys.path.insert(0, _mirofish_path)

from celery import Task
from workers.celery_app import celery_app
from core.config import settings
import redis as redis_sync
import structlog

logger = structlog.get_logger()
redis_client = redis_sync.from_url(settings.redis_url)


async def _simulation_row_exists(db, sim_uuid: uuid.UUID) -> bool:
    from sqlalchemy import select
    from models.simulation import Simulation

    r = await db.execute(select(Simulation.id).where(Simulation.id == sim_uuid))
    return r.scalar_one_or_none() is not None


async def _simulation_status_is(db, sim_uuid: uuid.UUID, expected) -> bool:
    from sqlalchemy import select
    from models.simulation import Simulation

    r = await db.execute(select(Simulation.status).where(Simulation.id == sim_uuid))
    st = r.scalar_one_or_none()
    return st is not None and st == expected


class SimulationTask(Task):
    abstract = True
    max_retries = 2
    default_retry_delay = 30


@celery_app.task(bind=True, base=SimulationTask, name="run_simulation")
def run_simulation(self, simulation_id: str):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_simulation_async(simulation_id, self))
    finally:
        loop.close()
        # NOTE: engine.dispose() is intentionally NOT called here.
        # The connection pool is shared across tasks in this worker process.
        # It is disposed only on worker shutdown via the signal handler below.


def run_simulation_inline(simulation_id: str) -> None:
    """Run the full simulation in a background thread when Celery broker is unavailable (local dev)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_simulation_async(simulation_id, None))
    finally:
        loop.close()


async def _run_simulation_async(simulation_id: str, task: Task | None):
    from core.database import AsyncSessionLocal
    from models.simulation import Simulation, SimulationStatus, SimulationEvent
    from services.seed_builder import build_seed
    from services.persona_generator import generate_personas
    from services.report_generator import generate_report
    from services.simulation_errors import user_facing_simulation_error
    from simulation_engine.mirofish_adapter import MiroFishAdapter
    from simulation_engine.cost_governor import CostGovernor
    from schemas.simulation import SimulationCreateRequest
    from sqlalchemy import select
    from datetime import datetime, timezone

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Simulation).where(Simulation.id == uuid.UUID(simulation_id))
        )
        sim = result.scalar_one_or_none()
        if not sim:
            logger.error("simulation_not_found", simulation_id=simulation_id)
            return

        try:
            if not await _simulation_status_is(db, sim.id, SimulationStatus.QUEUED):
                logger.info(
                    "simulation_worker_skip_entry_status",
                    simulation_id=simulation_id,
                )
                return

            await _update_status(db, sim, SimulationStatus.BUILDING_SEED)
            _emit_progress(simulation_id, "Building market context from your inputs...", 5)

            request = SimulationCreateRequest(
                business_name=sim.business_name,
                idea_description=sim.idea_description,
                target_market=sim.target_market,
                pricing_model=sim.pricing_model,
                price_points=sim.price_points,
                gtm_channels=sim.gtm_channels,
                competitors=sim.competitors,
                key_assumptions=sim.key_assumptions,
                vertical=sim.vertical,
                agent_count=sim.agent_count,
                max_turns=sim.max_turns,
            )
            seed = await build_seed(request)
            if not await _simulation_status_is(db, sim.id, SimulationStatus.BUILDING_SEED):
                logger.info("simulation_worker_abort_after_seed", simulation_id=simulation_id)
                return
            _emit_progress(simulation_id, "Market context built. Generating customer profiles...", 15)

            await _update_status(db, sim, SimulationStatus.GENERATING_PERSONAS)
            personas = sim.personas if sim.personas else await generate_personas(
                sim.vertical, sim.target_market, sim.idea_description, sim.agent_count
            )
            sim.personas = personas
            await db.commit()
            if not await _simulation_status_is(db, sim.id, SimulationStatus.GENERATING_PERSONAS):
                logger.info("simulation_worker_abort_after_personas", simulation_id=simulation_id)
                return
            _emit_progress(simulation_id, f"Generated {len(personas)} customer agents. Starting simulation...", 25)

            if not await _simulation_status_is(db, sim.id, SimulationStatus.GENERATING_PERSONAS):
                logger.info("simulation_worker_abort_before_run", simulation_id=simulation_id)
                return

            await _update_status(db, sim, SimulationStatus.RUNNING)
            cost_governor = CostGovernor(max_cost_usd=settings.max_cost_per_simulation_usd)
            adapter = MiroFishAdapter(seed=seed, personas=personas, cost_governor=cost_governor)

            events_collected = []
            async for turn_result in adapter.run(max_turns=sim.max_turns):
                if not await _simulation_status_is(db, sim.id, SimulationStatus.RUNNING):
                    logger.info(
                        "simulation_worker_stopping_turn_loop",
                        simulation_id=simulation_id,
                    )
                    return

                if cost_governor.is_over_limit():
                    logger.warning("cost_limit_reached", simulation_id=simulation_id)
                    break

                turn_events = []
                for event_data in turn_result.get("events", []):
                    event = SimulationEvent(
                        simulation_id=sim.id,
                        turn=turn_result["turn"],
                        agent_name=event_data.get("agent_name", "Unknown"),
                        agent_segment=event_data.get("segment", "unknown"),
                        event_type=event_data.get("event_type", "unknown"),
                        event_description=event_data.get("description", ""),
                    )
                    db.add(event)
                    turn_events.append(event)
                    events_collected.append(event)

                sim.current_turn = turn_result["turn"]
                sim.agents_active = turn_result.get("agents_active", 0)
                sim.actual_cost_usd = cost_governor.total_cost_usd
                await db.commit()

                progress_pct = 25 + int((turn_result["turn"] / sim.max_turns) * 55)
                _emit_turn_update(
                    simulation_id,
                    turn_result,
                    turn_events,
                    progress_pct,
                    max_turns=sim.max_turns,
                    agent_count=sim.agent_count,
                )
                logger.info(
                    "simulation_turn_done",
                    simulation_id=simulation_id,
                    turn=turn_result["turn"],
                    max_turns=sim.max_turns,
                    events_persisted=len(turn_events),
                )

            if not await _simulation_status_is(db, sim.id, SimulationStatus.RUNNING):
                logger.info("simulation_worker_skip_report_phase", simulation_id=simulation_id)
                return

            await _update_status(db, sim, SimulationStatus.GENERATING_REPORT)
            _emit_progress(simulation_id, "Simulation complete. Building your report...", 85)

            report = await generate_report(sim, events_collected, db)

            sim.status = SimulationStatus.COMPLETED
            sim.completed_at = datetime.now(timezone.utc)
            await db.commit()

            _emit_progress(simulation_id, "Report ready!", 100, report_id=str(report.id))
            logger.info("simulation_completed", simulation_id=simulation_id, cost=sim.actual_cost_usd)

            if sim.notify_on_complete:
                try:
                    from services.email_service import send_simulation_complete
                    from models.user import User
                    user_result = await db.execute(
                        select(User).where(User.id == sim.user_id)
                    )
                    user = user_result.scalar_one_or_none()
                    if user and user.email:
                        await send_simulation_complete(
                            to_email=user.email,
                            user_name=user.full_name or "there",
                            business_name=sim.business_name,
                            report_url=f"https://futurus.dev/simulation/{sim.id}/report",
                            adoption_rate=report.summary_metrics.get("adoption_rate", 0),
                        )
                except Exception as email_err:
                    logger.warning("email_send_failed", error=str(email_err))

        except Exception as e:
            logger.exception("simulation_failed", simulation_id=simulation_id, error=str(e))
            r = await db.execute(
                select(Simulation).where(Simulation.id == uuid.UUID(simulation_id))
            )
            s = r.scalar_one_or_none()
            if not s:
                logger.info("simulation_gone_after_error", simulation_id=simulation_id)
                return
            s.status = SimulationStatus.FAILED
            s.error_message = user_facing_simulation_error(e)
            await db.commit()
            # SECURITY: Generic message on pub/sub; full error stays in DB only
            _emit_progress(simulation_id, "Simulation encountered an error.", -1)
            raise


async def _update_status(db, sim, status):
    from models.simulation import SimulationStatus
    from datetime import datetime, timezone

    sim.status = status
    if status == SimulationStatus.RUNNING:
        sim.started_at = datetime.now(timezone.utc)
    await db.commit()


def _emit_progress(simulation_id: str, message: str, progress: int, report_id: str = None):
    # SECURITY: Never publish raw exception strings to Redis (WebSocket subscribers)
    safe_message = message
    if progress == -1:
        safe_message = "Simulation encountered an error. Please try again."
    payload = json.dumps({
        "type": "progress",
        "message": safe_message,
        "progress": progress,
        "report_id": report_id,
    })
    try:
        redis_client.publish(f"sim:{simulation_id}", payload)
    except Exception:
        pass


def _emit_turn_update(
    simulation_id: str,
    turn_result: dict,
    events: list,
    progress: int,
    *,
    max_turns: int,
    agent_count: int,
):
    payload = json.dumps({
        "type": "turn",
        "turn": turn_result["turn"],
        "progress": progress,
        "agents_active": turn_result.get("agents_active", 0),
        "max_turns": max_turns,
        "agent_count": agent_count,
        "events": [
            {
                "agent_name": e.agent_name,
                "segment": e.agent_segment,
                "event_type": e.event_type,
                "description": e.event_description,
            }
            for e in events[:10]
        ],
    })
    try:
        redis_client.publish(f"sim:{simulation_id}", payload)
    except Exception:
        pass


from celery.signals import worker_shutdown


@worker_shutdown.connect
def on_worker_shutdown(sender, **kwargs):
    """Dispose DB connection pool cleanly when the Celery worker stops."""
    import asyncio
    from core.database import engine
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(engine.dispose())
    finally:
        loop.close()
