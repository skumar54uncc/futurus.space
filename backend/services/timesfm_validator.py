"""TimesFM-based statistical trajectory validation (from cloned repo).

Compares simulated adoption curves against Google's TimesFM foundation model
to detect when AI agents are overly optimistic vs. statistical forecasts.
Falls back to lightweight heuristics if model unavailable.
"""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from statistics import mean
from typing import Any

import numpy as np
import structlog

logger = structlog.get_logger()

# Add cloned TimesFM repo to path
TIMESFM_REPO_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "vendors", "timesfm", "src")
if TIMESFM_REPO_PATH not in sys.path and os.path.exists(TIMESFM_REPO_PATH):
    sys.path.insert(0, TIMESFM_REPO_PATH)


def _timesfm_mode() -> str:
    """Validation mode: heuristic | auto | full.

    heuristic: always use lightweight check (fastest)
    auto: use heuristic for short curves, full model for richer curves
    full: always attempt model inference first
    """
    mode = os.getenv("FUTURUS_TIMESFM_MODE", "heuristic").strip().lower()
    if mode in {"heuristic", "auto", "full"}:
        return mode
    return "heuristic"


def _env_int(name: str, default: int, *, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        value = int((os.getenv(name, str(default)) or str(default)).strip())
    except Exception:
        value = default
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _env_bool(name: str, default: bool) -> bool:
    value = (os.getenv(name, "1" if default else "0") or "").strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


def _timesfm_params() -> dict[str, Any]:
    """Runtime-tunable TimesFM parameters via env vars."""
    return {
        "horizon": _env_int("FUTURUS_TIMESFM_HORIZON", 12, minimum=4, maximum=64),
        "max_context": _env_int("FUTURUS_TIMESFM_MAX_CONTEXT", 512, minimum=64, maximum=2048),
        "max_horizon": _env_int("FUTURUS_TIMESFM_MAX_HORIZON", 32, minimum=8, maximum=256),
        "auto_min_points": _env_int("FUTURUS_TIMESFM_AUTO_MIN_POINTS", 12, minimum=4, maximum=200),
        "normalize_inputs": _env_bool("FUTURUS_TIMESFM_NORMALIZE_INPUTS", True),
        "use_continuous_quantile_head": _env_bool("FUTURUS_TIMESFM_CONTINUOUS_QUANTILE_HEAD", True),
        "force_flip_invariance": _env_bool("FUTURUS_TIMESFM_FORCE_FLIP_INVARIANCE", True),
        "infer_is_positive": _env_bool("FUTURUS_TIMESFM_INFER_POSITIVE", True),
        "fix_quantile_crossing": _env_bool("FUTURUS_TIMESFM_FIX_QUANTILE_CROSSING", True),
    }


def _series_from_adoption_curve(adoption_curve: list[dict]) -> list[float]:
    """Extract numeric adoption values from curve."""
    series: list[float] = []
    for row in adoption_curve:
        try:
            series.append(float(row.get("cumulative", row.get("adopters", 0))))
        except Exception:
            continue
    return series


def _heuristic_validation(series: list[float], reason: str = "") -> dict[str, Any]:
    """Lightweight slope-based fallback when model unavailable."""
    if len(series) < 4:
        return {
            "enabled": False,
            "method": "heuristic",
            "risk_level": "low",
            "divergence_score": 0,
            "summary": "Not enough points for a meaningful trajectory check.",
            "forecast": [],
            "quantiles": {},
            "fallback_reason": reason,
        }

    diffs = [series[i] - series[i - 1] for i in range(1, len(series))]
    recent = diffs[-3:] if len(diffs) >= 3 else diffs
    recent_growth = mean(recent) if recent else 0.0
    projected = series[-1] + (recent_growth * 12)
    slope_gap = abs(projected - series[-1]) / max(1.0, series[-1])
    divergence_score = max(0, min(100, round(slope_gap * 70)))
    risk_level = "high" if divergence_score >= 65 else ("medium" if divergence_score >= 35 else "low")

    return {
        "enabled": False,
        "method": "heuristic",
        "risk_level": risk_level,
        "divergence_score": divergence_score,
        "summary": (
            f"Recent growth averages {recent_growth:.1f} per turn; statistical check suggests a possible plateau."
        ),
        "forecast": [round(projected, 1)] * 12,
        "quantiles": {
            "p10": round(projected * 0.85, 1),
            "p50": round(projected, 1),
            "p90": round(projected * 1.10, 1),
        },
        "fallback_reason": reason,
    }


@lru_cache(maxsize=1)
def _load_timesfm_model(params_key: tuple):
    """Load TimesFM 2.5 from cloned repo or HuggingFace."""
    try:
        from timesfm.timesfm_2p5.timesfm_2p5_torch import TimesFM_2p5_200M_torch
        from timesfm.configs import ForecastConfig
    except ImportError as exc:
        logger.warning("timesfm_import_failed", error=str(exc))
        return None, None

    try:
        # Try loading from local checkpoint first (if available)
        local_checkpoint = os.path.join(
            os.path.dirname(__file__), "..", "..", "vendors", "timesfm", "timesfm-2.5-200m-pytorch"
        )
        if os.path.exists(local_checkpoint):
            logger.info("loading_timesfm_from_local_checkpoint", path=local_checkpoint)
            model = TimesFM_2p5_200M_torch.from_pretrained(local_checkpoint)
        else:
            # Fall back to HuggingFace Hub
            logger.info("loading_timesfm_from_huggingface")
            try:
                # Try with minimal kwargs to avoid compatibility issues
                model = TimesFM_2p5_200M_torch.from_pretrained(
                    "google/timesfm-2.5-200m-pytorch",
                    local_files_only=False,
                    token=None,
                )
            except TypeError as te:
                if "unexpected keyword argument" in str(te):
                    # Fallback: manual loading
                    logger.warning("timesfm_from_pretrained_incompatibility", error=str(te))
                    from huggingface_hub import hf_hub_download
                    
                    model_path = hf_hub_download(
                        repo_id="google/timesfm-2.5-200m-pytorch",
                        filename="model.safetensors",
                    )
                    model = TimesFM_2p5_200M_torch(torch_compile=False)
                    model.model.load_checkpoint(model_path, torch_compile=False)
                else:
                    raise

        params = dict(params_key)
        config = ForecastConfig(
            max_context=int(params["max_context"]),
            max_horizon=int(params["max_horizon"]),
            normalize_inputs=bool(params["normalize_inputs"]),
            use_continuous_quantile_head=bool(params["use_continuous_quantile_head"]),
            force_flip_invariance=bool(params["force_flip_invariance"]),
            infer_is_positive=bool(params["infer_is_positive"]),
            fix_quantile_crossing=bool(params["fix_quantile_crossing"]),
        )
        logger.info("timesfm_model_loaded_successfully")
        return model, config
    except Exception as exc:
        logger.warning("timesfm_model_load_failed", error=str(exc), error_type=type(exc).__name__)
        return None, None


def build_timesfm_validation(adoption_curve: list[dict], summary_metrics: dict[str, Any]) -> dict[str, Any]:
    """Run TimesFM forecast and compare against simulated trajectory."""
    series = _series_from_adoption_curve(adoption_curve)
    mode = _timesfm_mode()
    params = _timesfm_params()

    if mode == "heuristic":
        result = _heuristic_validation(series, reason="timesfm_mode_heuristic")
        result["timesfm_parameters"] = params
        return result

    if mode == "auto" and len(series) < int(params["auto_min_points"]):
        result = _heuristic_validation(series, reason="timesfm_mode_auto_short_curve")
        result["timesfm_parameters"] = params
        return result

    if len(series) < 4:
        result = _heuristic_validation(series, reason="insufficient_data_points")
        result["timesfm_parameters"] = params
        return result

    model, config = _load_timesfm_model(tuple(sorted(params.items())))
    if model is None or config is None:
        result = _heuristic_validation(series, reason="model_load_failed")
        result["timesfm_parameters"] = params
        return result

    try:
        # Prepare input as numpy float32
        input_series = np.array(series, dtype=np.float32)

        # TimesFM expects list of series and horizon
        inputs = [input_series]
        horizon = int(params["horizon"])

        # Model must be compiled first with config
        model.compile(config)

        # Run forecast: returns (point_forecast, quantile_forecast)
        # point_forecast shape: (batch, horizon)
        # quantile_forecast shape: (batch, horizon, num_quantiles)
        point_forecast, quantile_forecast = model.forecast(
            horizon=horizon,
            inputs=inputs,
        )

        point_values = point_forecast[0].tolist()
        quantile_values = quantile_forecast[0].tolist() if quantile_forecast is not None else []

        # Calculate divergence: how much does the forecast deviate from recent trajectory?
        recent_window = series[-3:] if len(series) >= 3 else series
        recent_growth = (
            mean([recent_window[i] - recent_window[i - 1] for i in range(1, len(recent_window))])
            if len(recent_window) > 1
            else 0.0
        )

        forecast_final = point_values[-1] if point_values else series[-1]
        future_growth = forecast_final - series[-1]
        
        # Avoid division by zero
        growth_denominator = max(1.0, abs(recent_growth) + 1.0)
        growth_gap = abs(future_growth - recent_growth) / growth_denominator
        
        # Map gap to 0-100 score
        divergence_score = max(0, min(100, round(growth_gap * 72)))
        risk_level = (
            "high" if divergence_score >= 65
            else ("medium" if divergence_score >= 35 else "low")
        )

        # Extract quantiles (TimesFM provides 10 quantiles)
        p10, p50, p90 = 0.0, forecast_final, 0.0
        if quantile_values and len(quantile_values[-1]) >= 10:
            last_step_quantiles = quantile_values[-1]
            p10 = float(last_step_quantiles[0])      # 10th percentile
            p50 = float(last_step_quantiles[4])      # 50th percentile (median)
            p90 = float(last_step_quantiles[8])      # 90th percentile

        return {
            "enabled": True,
            "method": "timesfm_2p5_torch",
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
    except Exception as exc:
        logger.warning("timesfm_forecast_failed_fallback_to_heuristic", error=str(exc))
        result = _heuristic_validation(series, reason=f"forecast_error: {str(exc)[:50]}")
        result["timesfm_parameters"] = params
        return result
