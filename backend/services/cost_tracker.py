"""Tracks LLM spend per simulation, per user, and globally."""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.simulation import Simulation
import uuid

logger = structlog.get_logger()

PRICE_PER_1K_INPUT = {"gpt-4o": 0.0025, "gpt-4o-mini": 0.00015}
PRICE_PER_1K_OUTPUT = {"gpt-4o": 0.01, "gpt-4o-mini": 0.0006}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    input_cost = (input_tokens / 1000) * PRICE_PER_1K_INPUT.get(model, 0.003)
    output_cost = (output_tokens / 1000) * PRICE_PER_1K_OUTPUT.get(model, 0.012)
    return round(input_cost + output_cost, 6)


async def update_simulation_cost(
    simulation_id: uuid.UUID, cost_usd: float, db: AsyncSession
) -> None:
    result = await db.execute(
        select(Simulation).where(Simulation.id == simulation_id)
    )
    sim = result.scalar_one_or_none()
    if sim:
        sim.actual_cost_usd = round(sim.actual_cost_usd + cost_usd, 6)
        await db.commit()
        logger.info(
            "cost_updated",
            simulation_id=str(simulation_id),
            added=cost_usd,
            total=sim.actual_cost_usd,
        )
