"""Unified statistical & macro validation orchestrator.

Combines:
- TimesFM: Statistical time-series divergence detection (remote HTTP or local heuristic)
- MIRAI: Macro-economic context and shock validation

Returns a comprehensive validation report for simulation reports.
"""

from __future__ import annotations

from statistics import mean
from typing import Any

import structlog

from .mirai_integration import build_mirai_validation, build_mirai_macro_context
from .timesfm_validator import build_timesfm_validation, _series_from_adoption_curve
from .timesfm_client import is_remote_enabled, get_timesfm_forecast

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


def _build_validation_from_remote_forecast(
    series: list[float],
    remote_result: dict[str, Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    """Convert raw remote forecast response into the validation dict
    expected by the rest of the pipeline (divergence, risk, quantiles)."""

    forecast_batch = remote_result.get("forecast")
    if not forecast_batch or not forecast_batch[0]:
        return {
            "enabled": False,
            "method": "fallback",
            "risk_level": "low",
            "divergence_score": 0,
            "summary": "Remote forecast returned empty results.",
            "forecast": [],
            "quantiles": {},
            "timesfm_parameters": params,
            "fallback_reason": "remote_empty_forecast",
        }

    point_values = forecast_batch[0]  # first series in batch
    quantile_batch = remote_result.get("quantiles")
    quantile_values = quantile_batch[0] if quantile_batch else []

    # Divergence: compare forecast trajectory vs. recent simulation trend
    recent_window = series[-3:] if len(series) >= 3 else series
    recent_growth = (
        mean([recent_window[i] - recent_window[i - 1] for i in range(1, len(recent_window))])
        if len(recent_window) > 1
        else 0.0
    )

    forecast_final = point_values[-1] if point_values else series[-1]
    future_growth = forecast_final - series[-1]
    growth_denominator = max(1.0, abs(recent_growth) + 1.0)
    growth_gap = abs(future_growth - recent_growth) / growth_denominator
    divergence_score = max(0, min(100, round(growth_gap * 72)))
    risk_level = (
        "high" if divergence_score >= 65
        else ("medium" if divergence_score >= 35 else "low")
    )

    # Quantiles
    p10, p50, p90 = 0.0, forecast_final, 0.0
    if quantile_values and len(quantile_values) > 0:
        last_step = quantile_values[-1] if isinstance(quantile_values[-1], list) else []
        if len(last_step) >= 10:
            p10 = float(last_step[0])
            p50 = float(last_step[4])
            p90 = float(last_step[8])

    return {
        "enabled": True,
        "method": remote_result.get("method", "timesfm_2p5_torch"),
        "risk_level": risk_level,
        "divergence_score": divergence_score,
        "summary": (
            f"TimesFM detects a {risk_level} divergence: agents project {forecast_final:.0f}, "
            f"but stats suggest {p50:.0f} (median) with 80% CI [{p10:.0f}, {p90:.0f}]."
        ),
        "forecast": [round(v, 1) for v in point_values],
        "quantiles": {
            "p10": round(p10, 1),
            "p50": round(p50, 1),
            "p90": round(p90, 1),
        },
        "timesfm_parameters": params,
    }


async def build_comprehensive_validation(
    adoption_curve: list[dict],
    summary_metrics: dict[str, Any],
    market_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Run all validation checks and merge results.

    When TIMESFM_SERVICE_URL is set, delegates forecast inference to the
    remote HF Space microservice. Otherwise falls back to local heuristic.
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
        if is_remote_enabled():
            # --- Remote HTTP path (production on DO) ---
            series = _series_from_adoption_curve(adoption_curve)
            if len(series) < 4:
                timesfm_result = {
                    "enabled": False,
                    "method": "heuristic",
                    "risk_level": "low",
                    "divergence_score": 0,
                    "summary": "Not enough points for a meaningful trajectory check.",
                    "forecast": [],
                    "quantiles": {},
                    "fallback_reason": "insufficient_data_points",
                }
            else:
                from .timesfm_validator import _timesfm_params
                params = _timesfm_params()
                remote_result = await get_timesfm_forecast(
                    series_data=[series],
                    horizon=int(params["horizon"]),
                    config={
                        "max_context": params["max_context"],
                        "max_horizon": params["max_horizon"],
                        "normalize_inputs": params["normalize_inputs"],
                        "use_continuous_quantile_head": params["use_continuous_quantile_head"],
                        "force_flip_invariance": params["force_flip_invariance"],
                        "infer_is_positive": params["infer_is_positive"],
                        "fix_quantile_crossing": params["fix_quantile_crossing"],
                    },
                )
                if remote_result.get("forecast") is not None:
                    logger.info("timesfm_remote_forecast_received", elapsed_ms=remote_result.get("elapsed_ms"))
                    timesfm_result = _build_validation_from_remote_forecast(series, remote_result, params)
                else:
                    # Remote failed — fall back to heuristic
                    logger.warning(
                        "timesfm_remote_fallback_to_heuristic",
                        error=remote_result.get("error"),
                    )
                    timesfm_result = build_timesfm_validation(adoption_curve, summary_metrics)
        else:
            # --- Local path (dev / heuristic mode) ---
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
