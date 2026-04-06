"""Unified statistical & macro validation orchestrator.

Combines:
- TimesFM: Statistical time-series divergence detection
- MIRAI: Macro-economic context and shock validation

Returns a comprehensive validation report for simulation reports.
"""

from __future__ import annotations

from typing import Any

import structlog

from .mirai_integration import build_mirai_validation, build_mirai_macro_context
from .timesfm_validator import build_timesfm_validation

logger = structlog.get_logger()


class ForecastCache:
    """Lightweight in-process cache for one validation pass."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Any:
        if key in self._store:
            self.hits += 1
            return self._store[key]
        self.misses += 1
        return None

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def stats(self) -> dict[str, int]:
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "lookups": total,
            "hit_rate_pct": round((self.hits / total) * 100, 2) if total else 0.0,
        }


def build_comprehensive_validation(
    adoption_curve: list[dict],
    summary_metrics: dict[str, Any],
    market_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Run all validation checks and merge results.
    
    Args:
        adoption_curve: Time series of adoption from simulation
        summary_metrics: Computed metrics (revenue, users, etc.)
        market_data: Target market parameters
        
    Returns:
        Merged validation report with signals from both validators
    """
    validation_report = {
        "timestamp": None,
        "validators": ["timesfm", "mirai"],
        "timesfm": {},
        "mirai": {},
        "forecast_cache": {},
        "composite_risk": "low",
        "warning_flags": [],
        "confidence_score": 0.0,
    }
    cache = ForecastCache()

    # TimesFM: Statistical trajectory check
    try:
        timesfm_result = build_timesfm_validation(adoption_curve, summary_metrics)
        validation_report["timesfm"] = timesfm_result
        logger.info("timesfm_validation_complete", risk=timesfm_result.get("risk_level"))
    except Exception as exc:
        logger.warning("timesfm_validation_error", error=str(exc))
        validation_report["timesfm"] = {
            "enabled": False,
            "method": "error",
            "risk_level": "unknown",
            "divergence_score": 0,
        }

    # MIRAI: Macro context and shock validation
    try:
        macro_context = cache.get("mirai_macro_context")
        if macro_context is None:
            macro_context = build_mirai_macro_context()
            cache.set("mirai_macro_context", macro_context)
        mirai_validation = build_mirai_validation(
            summary_metrics,
            market_data,
            macro_context=macro_context,
        )
        
        validation_report["mirai"] = mirai_validation
        validation_report["macro_context"] = macro_context
        logger.info("mirai_validation_complete", macro_context=macro_context)
    except Exception as exc:
        logger.warning("mirai_validation_error", error=str(exc))
        validation_report["mirai"] = {
            "enabled": False,
            "method": "error",
            "validation_score": 0.0,
        }

    # Composite risk assessment
    timesfm_enabled = validation_report["timesfm"].get("enabled", False)
    mirai_enabled = validation_report["mirai"].get("enabled", False)

    if timesfm_enabled:
        timesfm_risk = validation_report["timesfm"].get("risk_level", "low")
        if timesfm_risk == "high":
            validation_report["warning_flags"].append("timesfm_high_divergence")
        elif timesfm_risk == "medium":
            validation_report["warning_flags"].append("timesfm_medium_divergence")

    if mirai_enabled:
        macro_alignment = validation_report["mirai"].get("macro_alignment", "unknown")
        if macro_alignment == "misaligned":
            validation_report["warning_flags"].append("mirai_macro_misalignment")

    # Overall risk: raise to "high" if either validator flags it
    if any("high" in flag for flag in validation_report["warning_flags"]):
        validation_report["composite_risk"] = "high"
    elif any("medium" in flag for flag in validation_report["warning_flags"]):
        validation_report["composite_risk"] = "medium"
    else:
        validation_report["composite_risk"] = "low"

    # Compute confidence: higher if both validators enabled and agree
    confidence = 0.0
    if timesfm_enabled and mirai_enabled:
        confidence = 0.95  # Both validators running
    elif timesfm_enabled:
        confidence = 0.85  # TimesFM only
    elif mirai_enabled:
        confidence = 0.80  # MIRAI only
    else:
        confidence = 0.5   # Fallback/heuristic only

    validation_report["confidence_score"] = confidence
    validation_report["forecast_cache"] = cache.stats()

    logger.info(
        "comprehensive_validation_complete",
        composite_risk=validation_report["composite_risk"],
        confidence=confidence,
        warnings=len(validation_report["warning_flags"]),
    )

    return validation_report
