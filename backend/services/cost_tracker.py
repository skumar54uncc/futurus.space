"""Tracks LLM spend per simulation, per user, and globally."""
from __future__ import annotations

import threading
import uuid
from collections import defaultdict

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.simulation import Simulation

logger = structlog.get_logger()

# Per-1K-token list prices (USD). Fireworks DeepSeek V4 Flash from model page:
# $0.14 / $0.03 / $0.28 per 1M (input / cached input / output).
PRICE_PER_1K_INPUT = {
    "gpt-4o": 0.0025,
    "gpt-4o-mini": 0.00015,
    "accounts/fireworks/models/deepseek-v4-flash": 0.00014,
    "deepseek-v4-flash": 0.00014,
    "llama-3.3-70b-versatile": 0.0,
    "llama-3.1-8b-instant": 0.0,
}
PRICE_PER_1K_CACHED_INPUT = {
    "accounts/fireworks/models/deepseek-v4-flash": 0.00003,
    "deepseek-v4-flash": 0.00003,
}
PRICE_PER_1K_OUTPUT = {
    "gpt-4o": 0.01,
    "gpt-4o-mini": 0.0006,
    "accounts/fireworks/models/deepseek-v4-flash": 0.00028,
    "deepseek-v4-flash": 0.00028,
    "llama-3.3-70b-versatile": 0.0,
    "llama-3.1-8b-instant": 0.0,
}

_lock = threading.Lock()
_provider_calls: dict[str, int] = defaultdict(int)
_estimated_cost_usd: float = 0.0
_input_tokens: int = 0
_cached_input_tokens: int = 0
_output_tokens: int = 0


def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    *,
    cached_input_tokens: int = 0,
) -> float:
    """Estimate USD cost. Cached input billed at the cheaper Fireworks cached rate when known."""
    cached = max(0, min(cached_input_tokens, input_tokens))
    uncached = max(0, input_tokens - cached)
    input_rate = PRICE_PER_1K_INPUT.get(model, 0.00014)
    cached_rate = PRICE_PER_1K_CACHED_INPUT.get(model, input_rate * 0.5)
    output_rate = PRICE_PER_1K_OUTPUT.get(model, 0.00028)
    input_cost = (uncached / 1000) * input_rate + (cached / 1000) * cached_rate
    output_cost = (output_tokens / 1000) * output_rate
    return round(input_cost + output_cost, 6)


def record_llm_usage(
    provider: str,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cached_input_tokens: int = 0,
) -> float:
    """Record a completed call for admin/provider-mix reporting. Returns estimated USD."""
    global _estimated_cost_usd, _input_tokens, _cached_input_tokens, _output_tokens
    cost = estimate_cost(
        model, input_tokens, output_tokens, cached_input_tokens=cached_input_tokens
    )
    with _lock:
        _provider_calls[provider] += 1
        _estimated_cost_usd = round(_estimated_cost_usd + cost, 6)
        _input_tokens += input_tokens
        _cached_input_tokens += cached_input_tokens
        _output_tokens += output_tokens
    return cost


def get_usage_snapshot() -> dict:
    """Process-local usage since last boot (Cloud Run instance lifetime)."""
    with _lock:
        return {
            "estimated_cost_usd": _estimated_cost_usd,
            "input_tokens": _input_tokens,
            "cached_input_tokens": _cached_input_tokens,
            "output_tokens": _output_tokens,
            "provider_calls": dict(_provider_calls),
            "note": "Totals reset when the Cloud Run instance cold-starts.",
        }


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
