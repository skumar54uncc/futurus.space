"""MIRAI macro intelligence framework integration.

Adapts MIRAI's event forecasting capability (from github.com/yecchen/MIRAI)
to inject geopolitical and macro context into business simulations.

MIRAI provides:
- International event forecasting using LLM agents
- GDELT event database access with temporal reasoning
- Structured event queries with reasoning chains

This module bridges MIRAI's international event signals to business macro shocks:
- Geopolitical tensions → growth slowdown
- Trade disruptions → inflation signals
- Regulatory changes → sentiment/risk adjustments
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any

import structlog

logger = structlog.get_logger()

# MIRAI repo paths
MIRAI_REPO_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "vendors", "mirai")
MIRAI_APIS_PATH = os.path.join(MIRAI_REPO_PATH, "APIs")

# Cache for macro signals
MACRO_SIGNALS_CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "static", "mirai_macro_signals.json")


@lru_cache(maxsize=1)
def _check_mirai_availability() -> bool:
    """Check if MIRAI repo is available and accessible."""
    if not os.path.exists(MIRAI_REPO_PATH):
        logger.info("mirai_repo_not_found", path=MIRAI_REPO_PATH)
        return False

    apis_path = os.path.join(MIRAI_REPO_PATH, "APIs", "api_implementation.py")
    if not os.path.exists(apis_path):
        logger.warning("mirai_api_not_found", path=apis_path)
        return False

    logger.info("mirai_repo_available", path=MIRAI_REPO_PATH)
    return True


def _geopolitical_event_to_macro_shock(event_type: str, severity: float) -> dict[str, float]:
    """
    Map geopolitical event types to macro shocks.

    Args:
        event_type: CAMEO event code or description
        severity: 0-1 intensity of the event

    Returns:
        dict with inflation_shock, growth_shock, sentiment_shock
    """
    shocks = {
        "inflation_shock": 0.0,
        "growth_shock": 0.0,
        "sentiment_shock": 0.0,
    }

    event_lower = event_type.lower()

    # Conflict events → growth slowdown + negative sentiment
    if any(x in event_lower for x in ["conflict", "war", "military", "attack", "protest"]):
        shocks["growth_shock"] = -0.3 * severity
        shocks["sentiment_shock"] = -0.4 * severity
        shocks["inflation_shock"] = 0.1 * severity  # Supply chain disruption

    # Trade/economic sanctions → inflation + disruption
    elif any(x in event_lower for x in ["embargo", "sanction", "trade", "tariff", "restrict"]):
        shocks["inflation_shock"] = 0.25 * severity
        shocks["growth_shock"] = -0.2 * severity
        shocks["sentiment_shock"] = -0.2 * severity

    # Diplomatic cooperation → growth acceleration
    elif any(x in event_lower for x in ["agree", "cooperat", "trade", "alliance", "meeting"]):
        shocks["growth_shock"] = 0.15 * severity
        shocks["sentiment_shock"] = 0.15 * severity
        shocks["inflation_shock"] = -0.05 * severity  # Better supply chains

    # Policy reform → positive but uncertain
    elif any(x in event_lower for x in ["reform", "deregulate", "policy"]):
        shocks["growth_shock"] = 0.1 * severity
        shocks["sentiment_shock"] = 0.1 * severity

    # Disaster events → inflation + disruption
    elif any(x in event_lower for x in ["disaster", "earthquake", "flood", "epidemic"]):
        shocks["inflation_shock"] = 0.2 * severity
        shocks["growth_shock"] = -0.15 * severity
        shocks["sentiment_shock"] = -0.25 * severity

    return shocks


def build_mirai_macro_context(
    market_countries: list[str] | None = None,
    forecast_days_ahead: int = 30
) -> dict[str, Any]:
    """
    Query MIRAI-style macro context for business simulation.

    Args:
        market_countries: List of countries relevant to the market (optional)
        forecast_days_ahead: How far ahead to consider (optional)

    Returns:
        dict with keys:
        - inflation_shock: float (-1 to +1), typical range [-0.5, 0.5]
        - growth_shock: float (-1 to +1), typical range [-0.5, 0.5]
        - sentiment_shock: float (-1 to +1), typical range [-0.5, 0.5]
        - confidence: float (0 to 1)
        - forecast_horizon: int (days ahead)
        - source: str (mirai_live, mirai_cache, mirai_unavailable, heuristic)
        - events_considered: list of event summaries
    """
    mirai_available = _check_mirai_availability()

    # Try to load from cache first
    if os.path.exists(MACRO_SIGNALS_CACHE_PATH):
        try:
            with open(MACRO_SIGNALS_CACHE_PATH, "r") as f:
                cached = json.load(f)
                cache_age = (
                    datetime.now() - datetime.fromisoformat(cached.get("cached_at", "2020-01-01"))
                ).total_seconds()
                
                # Cache valid if less than 24 hours old
                if cache_age < 86400:
                    logger.info("mirai_macro_context_from_cache", age_seconds=cache_age)
                    return {
                        **cached,
                        "source": "mirai_cache",
                    }
        except Exception as exc:
            logger.warning("mirai_cache_load_failed", error=str(exc))

    # If MIRAI not available, return heuristic
    if not mirai_available:
        return _heuristic_macro_context()

    # Try to run MIRAI analysis
    try:
        # For now, simulate MIRAI context with weighted defaults
        # In production, this would call MIRAI's agent/API interfaces
        result = _simulate_mirai_analysis(market_countries, forecast_days_ahead)
        result["date_generated"] = datetime.now().isoformat()
        result["cached_at"] = datetime.now().isoformat()

        # Cache the result
        os.makedirs(os.path.dirname(MACRO_SIGNALS_CACHE_PATH), exist_ok=True)
        with open(MACRO_SIGNALS_CACHE_PATH, "w") as f:
            json.dump(result, f, indent=2)

        return result
    except Exception as exc:
        logger.warning("mirai_analysis_failed", error=str(exc))
        return _heuristic_macro_context()


def _simulate_mirai_analysis(
    market_countries: list[str] | None = None,
    forecast_days_ahead: int = 30
) -> dict[str, Any]:
    """Simulate MIRAI analysis (placeholder for real MIRAI integration)."""
    # In production, this would:
    # 1. Query MIRAI's event KG for recent events
    # 2. Run agent reasoning on market-relevant countries
    # 3. Generate forecasts for specified horizon
    # 4. Return structured shocks

    # For now, return moderate baseline with small random variation
    import random

    events = [
        "Global supply chain normalization trend",
        "Moderate geopolitical tensions in select regions",
        "Mixed regulatory environment across markets",
    ]

    shocks = {
        "inflation_shock": random.uniform(-0.05, 0.1),
        "growth_shock": random.uniform(-0.05, 0.1),
        "sentiment_shock": random.uniform(-0.1, 0.05),
    }

    return {
        "inflation_shock": round(shocks["inflation_shock"], 3),
        "growth_shock": round(shocks["growth_shock"], 3),
        "sentiment_shock": round(shocks["sentiment_shock"], 3),
        "confidence": 0.45,  # Lower confidence for simulated analysis
        "forecast_horizon": forecast_days_ahead,
        "source": "mirai_simulated",
        "events_considered": events,
    }


def _heuristic_macro_context() -> dict[str, Any]:
    """Fallback heuristic when MIRAI unavailable."""
    return {
        "inflation_shock": 0.0,
        "growth_shock": 0.0,
        "sentiment_shock": 0.0,
        "confidence": 0.0,
        "forecast_horizon": 0,
        "source": "mirai_unavailable",
        "events_considered": [],
    }


def build_mirai_validation(
    forecast_data: dict[str, Any],
    market_data: dict[str, Any],
    macro_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Validate forecast credibility against MIRAI macro context.

    Args:
        forecast_data: Simulated economic forecast (revenue, growth, etc.)
        market_data: Target market parameters (region, sector, etc.)

    Returns:
        dict with validation alignment score
    """
    # Get current macro context (caller may pass a cached value).
    if macro_context is None:
        market_countries = market_data.get("countries", [])
        macro_context = build_mirai_macro_context(market_countries=market_countries)

    # If macro context is unavailable, skip validation
    if macro_context["source"] in {"mirai_unavailable", "heuristic"}:
        return {
            "enabled": False,
            "method": "mirai_unavailable",
            "validation_score": 0.0,
            "macro_alignment": "unknown",
            "confidence": 0.0,
            "macro_context": macro_context,
        }

    # Check if forecast assumptions align with macro shocks
    try:
        # Extract forecast growth rate
        forecast_growth = forecast_data.get("growth_rate", 0.15)  # Default 15%
        
        # Adjust for macro context
        macro_adjusted_growth = forecast_growth + macro_context["growth_shock"]
        
        # Compute alignment: how realistic is the forecast given macro?
        if macro_context["sentiment_shock"] < -0.3:
            # Significant headwinds
            if forecast_growth > 0.20:
                alignment = "pessimistic_forecast"  # Forecast too optimistic
                score = 0.4
            else:
                alignment = "aligned"
                score = 0.8
        elif macro_context["sentiment_shock"] > 0.2:
            # Tailwinds
            if forecast_growth < 0.10:
                alignment = "conservative_forecast"  # Forecast too cautious
                score = 0.5
            else:
                alignment = "aligned"
                score = 0.8
        else:
            # Neutral
            alignment = "aligned"
            score = 0.7

        return {
            "enabled": macro_context["source"] != "mirai_unavailable",
            "method": "mirai_macro_alignment",
            "validation_score": round(score, 2),
            "macro_alignment": alignment,
            "confidence": round(macro_context["confidence"], 2),
            "macro_context": macro_context,
            "forecast_summary": (
                f"In current macro context (growth_shock={macro_context['growth_shock']:.2f}, "
                f"sentiment_shock={macro_context['sentiment_shock']:.2f}), your {forecast_growth*100:.0f}% growth "
                f"forecast is {alignment}."
            ),
        }
    except Exception as exc:
        logger.warning("mirai_validation_error", error=str(exc))
        return {
            "enabled": False,
            "method": "error",
            "validation_score": 0.0,
            "macro_alignment": "error",
            "confidence": 0.0,
            "macro_context": macro_context,
        }
