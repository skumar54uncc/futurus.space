"""Runs 3x simulations, merges results for higher confidence."""
import asyncio
import statistics
from typing import AsyncGenerator
from simulation_engine.mirofish_adapter import MiroFishAdapter
from simulation_engine.cost_governor import CostGovernor
import structlog

logger = structlog.get_logger()


async def run_ensemble(
    seed: dict,
    personas: list,
    max_turns: int,
    ensemble_count: int,
    max_cost_usd: float,
) -> dict:
    per_run_budget = max_cost_usd / ensemble_count
    all_results: list[dict] = []

    for run_idx in range(ensemble_count):
        logger.info("ensemble_run_start", run=run_idx + 1, total=ensemble_count)
        cost_governor = CostGovernor(max_cost_usd=per_run_budget)
        adapter = MiroFishAdapter(seed=seed, personas=personas, cost_governor=cost_governor)

        run_events = []
        async for turn_result in adapter.run(max_turns=max_turns):
            run_events.extend(turn_result.get("events", []))

        all_results.append({
            "events": run_events,
            "cost": cost_governor.total_cost_usd,
        })

    merged = _merge_ensemble_results(all_results, len(personas), max_turns)
    return merged


def _merge_ensemble_results(results: list[dict], total_agents: int, max_turns: int) -> dict:
    adoption_rates = []
    churn_rates = []
    viral_coefficients = []

    for run in results:
        events = run["events"]
        adopted = sum(1 for e in events if e.get("event_type") == "adopted")
        churned = sum(1 for e in events if e.get("event_type") == "churned")
        referred = sum(1 for e in events if e.get("event_type") == "referred")

        adoption_rates.append((adopted / max(1, total_agents)) * 100)
        churn_rates.append((churned / max(1, adopted)) * 100)
        viral_coefficients.append(referred / max(1, adopted))

    return {
        "ensemble_variance": {
            "adoption_rate": _stats(adoption_rates),
            "churn_rate": _stats(churn_rates),
            "viral_coefficient": _stats(viral_coefficients),
        },
        "mean_adoption_rate": round(statistics.mean(adoption_rates), 1),
        "mean_churn_rate": round(statistics.mean(churn_rates), 1),
        "mean_viral_coefficient": round(statistics.mean(viral_coefficients), 2),
        "runs_completed": len(results),
        "total_cost": sum(r["cost"] for r in results),
    }


def _stats(values: list[float]) -> dict:
    if len(values) < 2:
        return {"mean": round(values[0], 2) if values else 0, "std_dev": 0, "min": round(values[0], 2) if values else 0, "max": round(values[0], 2) if values else 0}

    mean = statistics.mean(values)
    std_dev = statistics.stdev(values)
    return {
        "mean": round(mean, 2),
        "std_dev": round(std_dev, 2),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "confidence_interval_95": [
            round(mean - 1.96 * std_dev, 2),
            round(mean + 1.96 * std_dev, 2),
        ],
    }
