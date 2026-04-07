"""Tests for the remote TimesFM HTTP client.

Mocks the HTTP layer so tests run without a real HF Space.
"""

from __future__ import annotations

import pytest
import httpx
from unittest.mock import AsyncMock, patch

from services.timesfm_client import get_timesfm_forecast, warmup_timesfm, is_remote_enabled


SAMPLE_SERIES = [[10.0, 15.0, 25.0, 50.0, 120.0, 280.0, 550.0, 850.0]]
SAMPLE_FORECAST_RESPONSE = {
    "forecast": [[900.0, 950.0, 980.0, 1000.0, 1010.0, 1015.0, 1018.0, 1020.0]],
    "quantiles": [[[800, 810, 820, 830, 840, 850, 860, 870, 880, 890]]],
    "method": "timesfm_2p5_torch",
    "elapsed_ms": 142.3,
}


@pytest.fixture(autouse=True)
def _set_service_url(monkeypatch):
    """Ensure TIMESFM_SERVICE_URL is set for all tests."""
    monkeypatch.setenv("TIMESFM_SERVICE_URL", "https://test-timesfm.hf.space")
    # Reset the cached URL
    import services.timesfm_client as mod
    mod._TIMESFM_SERVICE_URL = ""


def test_is_remote_enabled():
    assert is_remote_enabled() is True


@pytest.mark.asyncio
async def test_successful_forecast():
    """Happy path: remote service returns a valid forecast."""
    mock_response = httpx.Response(200, json=SAMPLE_FORECAST_RESPONSE)

    with patch("services.timesfm_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await get_timesfm_forecast(SAMPLE_SERIES, horizon=8)

    assert result["method"] == "timesfm_2p5_torch"
    assert result["forecast"] is not None
    assert len(result["forecast"]) == 1
    assert len(result["forecast"][0]) == 8


@pytest.mark.asyncio
async def test_timeout_returns_fallback():
    """When HF Space is cold / slow, return fallback gracefully."""
    with patch("services.timesfm_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.side_effect = httpx.TimeoutException("read timeout")
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await get_timesfm_forecast(SAMPLE_SERIES, horizon=8)

    assert result["forecast"] is None
    assert result["method"] == "fallback"
    assert "timeout" in result["error"].lower()


@pytest.mark.asyncio
async def test_http_error_returns_fallback():
    """When HF Space returns 500, return fallback."""
    error_response = httpx.Response(500, json={"detail": "Model OOM"})
    error_response.request = httpx.Request("POST", "https://test-timesfm.hf.space/predict")

    with patch("services.timesfm_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = error_response
        # raise_for_status will raise
        instance.post.return_value.raise_for_status = lambda: (_ for _ in ()).throw(
            httpx.HTTPStatusError("Server Error", request=error_response.request, response=error_response)
        )
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await get_timesfm_forecast(SAMPLE_SERIES, horizon=8)

    assert result["forecast"] is None
    assert result["method"] == "fallback"
    assert "500" in result["error"]


@pytest.mark.asyncio
async def test_network_error_returns_fallback():
    """When network is unreachable, return fallback."""
    with patch("services.timesfm_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.side_effect = httpx.ConnectError("Connection refused")
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await get_timesfm_forecast(SAMPLE_SERIES, horizon=8)

    assert result["forecast"] is None
    assert result["method"] == "fallback"


@pytest.mark.asyncio
async def test_no_url_returns_fallback(monkeypatch):
    """When TIMESFM_SERVICE_URL is empty, return fallback immediately."""
    monkeypatch.setenv("TIMESFM_SERVICE_URL", "")
    import services.timesfm_client as mod
    mod._TIMESFM_SERVICE_URL = ""

    result = await get_timesfm_forecast(SAMPLE_SERIES, horizon=8)

    assert result["forecast"] is None
    assert result["method"] == "fallback"
    assert "not set" in result["error"]


@pytest.mark.asyncio
async def test_warmup_success():
    """Warmup sends health + dummy predict request."""
    health_response = httpx.Response(200, json={"status": "ok", "model": "test"})
    predict_response = httpx.Response(200, json={"forecast": [[1, 2, 3, 4]], "elapsed_ms": 50.0})

    with patch("services.timesfm_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.get.return_value = health_response
        instance.post.return_value = predict_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        # Should not raise
        await warmup_timesfm()

    instance.get.assert_called_once()
    instance.post.assert_called_once()


@pytest.mark.asyncio
async def test_warmup_failure_is_nonfatal():
    """Warmup failure should not crash the app."""
    with patch("services.timesfm_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.get.side_effect = httpx.TimeoutException("cold start")
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        # Should not raise
        await warmup_timesfm()


@pytest.mark.asyncio
async def test_config_forwarded():
    """Custom config should be sent in the request body."""
    mock_response = httpx.Response(200, json=SAMPLE_FORECAST_RESPONSE)

    with patch("services.timesfm_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        custom_config = {"max_context": 256, "normalize_inputs": False}
        await get_timesfm_forecast(SAMPLE_SERIES, horizon=16, config=custom_config)

    call_args = instance.post.call_args
    payload = call_args.kwargs.get("json") or call_args[1].get("json")
    assert payload["horizon"] == 16
    assert payload["config"] == custom_config
