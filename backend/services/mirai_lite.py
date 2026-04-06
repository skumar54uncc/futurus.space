"""Automated MIRAI-lite macro context.

This module keeps a small daily cache of global macro shocks and turns it into
MiroFish-friendly context using the existing VariableInjector.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import structlog

from core.config import settings
from simulation_engine.variable_injector import VariableInjector

logger = structlog.get_logger()

_CACHE_PATH = Path(__file__).resolve().parent.parent / "static" / "daily_macro_context.json"
_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
_CACHE_MAX_AGE = timedelta(hours=24)
_TAVILY_ENDPOINT = "https://api.tavily.com/search"
_TAVILY_TIMEOUT = 12.0


DEFAULT_SHOCKS: list[dict[str, str]] = [
    {
        "variable": "macro_inflation",
        "value": "elevated",
        "description": "Inflation pressure remains sticky in consumer-facing categories.",
    },
    {
        "variable": "tourism_demand",
        "value": "mixed",
        "description": "Tourism and event-driven demand is uneven across major cities.",
    },
    {
        "variable": "regulatory_pressure",
        "value": "rising",
        "description": "New compliance expectations are increasing for AI-enabled products.",
    },
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_cache() -> dict[str, Any] | None:
    if not _CACHE_PATH.exists():
        return None
    try:
        return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("mirai_lite_cache_read_failed")
        return None


def _is_cache_fresh(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False
    generated_at = payload.get("generated_at")
    if not isinstance(generated_at, str):
        return False
    try:
        ts = datetime.fromisoformat(generated_at)
    except Exception:
        return False
    return _now() - ts <= _CACHE_MAX_AGE


def _store_cache(payload: dict[str, Any]) -> None:
    _CACHE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


async def _tavily_search(client: httpx.AsyncClient, query: str) -> list[dict]:
    if not settings.tavily_api_key:
        return []
    try:
        resp = await client.post(
            _TAVILY_ENDPOINT,
            json={
                "api_key": settings.tavily_api_key,
                "query": query,
                "search_depth": "basic",
                "include_answer": False,
                "max_results": 3,
            },
            timeout=_TAVILY_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception as exc:
        logger.warning("mirai_lite_tavily_search_failed", query=query[:80], error=str(exc))
        return []


def _results_to_shocks(results: list[dict]) -> list[dict[str, str]]:
    shocks: list[dict[str, str]] = []
    seen: set[str] = set()
    for result in results:
        title = str(result.get("title") or "").strip()
        snippet = str(result.get("content") or result.get("snippet") or "").strip()
        if not title or not snippet:
            continue
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)

        text = f"{title}: {snippet[:220]}"
        lowered = f"{title} {snippet}".lower()
        if any(word in lowered for word in ("inflation", "price", "interest rate", "rates")):
            shocks.append({"variable": "macro_inflation", "value": "watch", "description": text})
        elif any(word in lowered for word in ("tourism", "travel", "hotel", "flight")):
            shocks.append({"variable": "tourism_demand", "value": "watch", "description": text})
        elif any(word in lowered for word in ("regulation", "policy", "ai act", "compliance")):
            shocks.append({"variable": "regulatory_pressure", "value": "watch", "description": text})
        if len(shocks) >= 3:
            break
    return shocks


async def refresh_daily_macro_context() -> dict[str, Any]:
    queries = [
        "global inflation outlook consumer demand 2026",
        "tourism demand outlook 2026 major cities",
        "AI regulation policy update 2026 startup",
    ]
    shocks: list[dict[str, str]] = []
    async with httpx.AsyncClient() as client:
        batches = await asyncio.gather(*[_tavily_search(client, q) for q in queries], return_exceptions=True)
    for batch in batches:
        if isinstance(batch, Exception):
            continue
        shocks.extend(_results_to_shocks(batch))

    if not shocks:
        shocks = DEFAULT_SHOCKS.copy()

    payload = {
        "generated_at": _now().isoformat(),
        "shocks": shocks[:3],
    }
    _store_cache(payload)
    logger.info("mirai_lite_context_refreshed", shocks=len(payload["shocks"]))
    return payload


async def load_or_refresh_daily_macro_context() -> dict[str, Any]:
    cached = _load_cache()
    if _is_cache_fresh(cached):
        return cached or {"generated_at": _now().isoformat(), "shocks": DEFAULT_SHOCKS.copy()}
    return await refresh_daily_macro_context()


async def build_daily_macro_context_modifier(target_market: str, vertical: str) -> str:
    payload = await load_or_refresh_daily_macro_context()
    shocks = payload.get("shocks", [])
    injector = VariableInjector({})
    for shock in shocks:
        injector.schedule(
            1,
            str(shock.get("variable") or "macro_signal"),
            str(shock.get("value") or "watch"),
            str(shock.get("description") or "Global market condition shifted."),
        )

    modifier = injector.build_context_modifier(1)
    if modifier:
        modifier = (
            f"{modifier}\n- Target market context: {target_market[:180]}\n"
            f"- Business vertical: {vertical.replace('_', ' ').title()}"
        )
    return modifier
