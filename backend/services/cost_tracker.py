"""Tracks LLM spend per simulation (persisted) and process-local admin snapshot."""
from __future__ import annotations

import threading
import uuid
from collections import defaultdict
from contextvars import ContextVar
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.simulation import Simulation

logger = structlog.get_logger()

# Bound to the active simulation worker so every call_llm can attribute cost.
current_simulation_id: ContextVar[str | None] = ContextVar(
    "current_simulation_id", default=None
)

# Per-1K-token list prices (USD). Fireworks DeepSeek V4 Flash:
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
# simulation_id -> usage bucket (survives until flushed to Postgres)
_sim_buckets: dict[str, dict[str, Any]] = {}


def _empty_bucket() -> dict[str, Any]:
    return {
        "by_provider": {},
        "calls": 0,
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "estimated_cost_usd": 0.0,
        "fallback_calls": 0,
    }


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


def begin_simulation_tracking(simulation_id: str) -> None:
    """Start attributing LLM calls to this simulation (call from the worker)."""
    sid = str(simulation_id)
    current_simulation_id.set(sid)
    with _lock:
        _sim_buckets[sid] = _empty_bucket()


def get_simulation_usage(simulation_id: str) -> dict[str, Any]:
    with _lock:
        bucket = _sim_buckets.get(str(simulation_id))
        return dict(bucket) if bucket else _empty_bucket()


def end_simulation_tracking(simulation_id: str) -> dict[str, Any]:
    """Stop context attribution and return the final usage snapshot (keeps bucket until pop)."""
    current_simulation_id.set(None)
    with _lock:
        return dict(_sim_buckets.get(str(simulation_id), _empty_bucket()))


def pop_simulation_tracking(simulation_id: str) -> dict[str, Any]:
    current_simulation_id.set(None)
    with _lock:
        return dict(_sim_buckets.pop(str(simulation_id), _empty_bucket()))


def record_llm_usage(
    provider: str,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cached_input_tokens: int = 0,
    *,
    simulation_id: str | None = None,
) -> float:
    """Record a completed call. Attributes to ContextVar / explicit simulation_id when set."""
    global _estimated_cost_usd, _input_tokens, _cached_input_tokens, _output_tokens
    cost = estimate_cost(
        model, input_tokens, output_tokens, cached_input_tokens=cached_input_tokens
    )
    sid = simulation_id or current_simulation_id.get()
    is_fallback = not str(provider).startswith("fireworks")

    with _lock:
        _provider_calls[provider] += 1
        _estimated_cost_usd = round(_estimated_cost_usd + cost, 6)
        _input_tokens += input_tokens
        _cached_input_tokens += cached_input_tokens
        _output_tokens += output_tokens

        if sid:
            bucket = _sim_buckets.setdefault(sid, _empty_bucket())
            bucket["calls"] += 1
            bucket["input_tokens"] += input_tokens
            bucket["cached_input_tokens"] += cached_input_tokens
            bucket["output_tokens"] += output_tokens
            bucket["estimated_cost_usd"] = round(
                float(bucket["estimated_cost_usd"]) + cost, 6
            )
            if is_fallback:
                bucket["fallback_calls"] += 1
            by_p = bucket["by_provider"]
            row = by_p.setdefault(
                provider,
                {
                    "model": model,
                    "calls": 0,
                    "input_tokens": 0,
                    "cached_input_tokens": 0,
                    "output_tokens": 0,
                    "estimated_cost_usd": 0.0,
                },
            )
            row["calls"] += 1
            row["input_tokens"] += input_tokens
            row["cached_input_tokens"] += cached_input_tokens
            row["output_tokens"] += output_tokens
            row["estimated_cost_usd"] = round(float(row["estimated_cost_usd"]) + cost, 6)
            row["model"] = model

    return cost


def get_usage_snapshot() -> dict:
    """Process-local usage since last boot (Cloud Run instance lifetime) — not interview proof alone."""
    with _lock:
        return {
            "estimated_cost_usd": _estimated_cost_usd,
            "input_tokens": _input_tokens,
            "cached_input_tokens": _cached_input_tokens,
            "output_tokens": _output_tokens,
            "provider_calls": dict(_provider_calls),
            "active_simulation_buckets": len(_sim_buckets),
            "note": (
                "Process-local totals reset on cold start. "
                "Per-simulation truth is simulations.actual_cost_usd + simulations.llm_usage."
            ),
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


async def persist_simulation_llm_usage(
    simulation_id: uuid.UUID, db: AsyncSession
) -> dict[str, Any]:
    """Write attributed LLM usage onto the simulation row (interview-provable)."""
    usage = pop_simulation_tracking(str(simulation_id))
    result = await db.execute(
        select(Simulation).where(Simulation.id == simulation_id)
    )
    sim = result.scalar_one_or_none()
    if not sim:
        return usage
    sim.llm_usage = usage
    # Prefer metered estimate when we have token usage; else keep CostGovernor estimate.
    metered = float(usage.get("estimated_cost_usd") or 0.0)
    if metered > 0:
        sim.actual_cost_usd = round(metered, 6)
    await db.commit()
    logger.info(
        "simulation_llm_usage_persisted",
        simulation_id=str(simulation_id),
        cost=sim.actual_cost_usd,
        calls=usage.get("calls"),
        providers=list((usage.get("by_provider") or {}).keys()),
        fallback_calls=usage.get("fallback_calls"),
    )
    return usage
