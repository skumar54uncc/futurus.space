"""Async HTTP client for the remote TimesFM forecasting microservice.

When TIMESFM_SERVICE_URL is set, the main backend delegates model inference
to a standalone Hugging Face Space instead of loading torch locally.
Falls back gracefully on timeout / cold-start / network errors.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

_TIMESFM_SERVICE_URL: str = ""


def _get_service_url() -> str:
    global _TIMESFM_SERVICE_URL
    if not _TIMESFM_SERVICE_URL:
        _TIMESFM_SERVICE_URL = (
            os.getenv("TIMESFM_SERVICE_URL", "").strip().rstrip("/")
        )
    return _TIMESFM_SERVICE_URL


def is_remote_enabled() -> bool:
    """True when TIMESFM_SERVICE_URL is configured."""
    return bool(_get_service_url())


async def get_timesfm_forecast(
    series_data: list[list[float]],
    horizon: int = 12,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call the remote TimesFM service and return raw forecast.

    Returns:
        On success: {"forecast": [...], "quantiles": [...], "method": "timesfm_2p5_torch"}
        On failure: {"forecast": None, "method": "fallback", "error": "<reason>"}
    """
    url = _get_service_url()
    if not url:
        return {"forecast": None, "method": "fallback", "error": "TIMESFM_SERVICE_URL not set"}

    payload: dict[str, Any] = {
        "series": series_data,
        "horizon": horizon,
    }
    if config:
        payload["config"] = config

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            logger.info("timesfm_http_call_start", url=url, horizon=horizon, series_count=len(series_data))
            resp = await client.post(f"{url}/predict", json=payload)
            resp.raise_for_status()
            data = resp.json()
            logger.info(
                "timesfm_http_call_complete",
                method=data.get("method"),
                elapsed_ms=data.get("elapsed_ms"),
            )
            return data

    except httpx.TimeoutException:
        logger.warning("timesfm_http_timeout", url=url, timeout_s=30)
        return {"forecast": None, "method": "fallback", "error": "TimesFM service timeout (cold start?)"}

    except httpx.HTTPStatusError as exc:
        detail = ""
        try:
            detail = exc.response.json().get("detail", "")
        except Exception:
            detail = exc.response.text[:200]
        logger.warning("timesfm_http_error", status=exc.response.status_code, detail=detail)
        return {"forecast": None, "method": "fallback", "error": f"HTTP {exc.response.status_code}: {detail}"}

    except Exception as exc:
        logger.warning("timesfm_http_unexpected_error", error=str(exc), error_type=type(exc).__name__)
        return {"forecast": None, "method": "fallback", "error": str(exc)[:200]}


async def warmup_timesfm() -> None:
    """Send a dummy request to wake up the HF Space (free tier sleeps after ~15 min)."""
    url = _get_service_url()
    if not url:
        logger.info("timesfm_warmup_skipped", reason="TIMESFM_SERVICE_URL not set")
        return

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(45.0, connect=10.0)) as client:
            logger.info("timesfm_warmup_start", url=url)
            # Health check first (fast, wakes the container)
            health_resp = await client.get(f"{url}/health")
            health_resp.raise_for_status()
            logger.info("timesfm_warmup_health_ok", status=health_resp.json())

            # Dummy forecast to load model weights into memory
            resp = await client.post(
                f"{url}/predict",
                json={"series": [[1, 2, 3, 4, 5, 6, 7, 8]], "horizon": 4},
            )
            resp.raise_for_status()
            logger.info("timesfm_warmup_complete", elapsed_ms=resp.json().get("elapsed_ms"))

    except Exception as exc:
        # Warmup failure is non-fatal — first real request will just be slower
        logger.warning("timesfm_warmup_failed", error=str(exc), error_type=type(exc).__name__)
