"""TimesFM forecasting microservice for Hugging Face Spaces.

Serves Google's TimesFM 2.5 200M (PyTorch, CPU) behind a simple FastAPI
endpoint so the main Futurus backend can call it over HTTP instead of
bundling torch in the DigitalOcean build.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("timesfm-service")

# ---------------------------------------------------------------------------
# Model singleton — loaded once at startup
# ---------------------------------------------------------------------------
_model = None
_MODEL_ID = "google/timesfm-2.5-200m-pytorch"


def _load_model():
    global _model
    logger.info("Loading TimesFM model from HuggingFace Hub: %s", _MODEL_ID)
    t0 = time.perf_counter()

    import timesfm

    _model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(_MODEL_ID)
    elapsed = time.perf_counter() - t0
    logger.info("TimesFM model loaded in %.1fs", elapsed)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_model()
    yield


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Futurus TimesFM Service",
    description="Standalone forecasting microservice powered by TimesFM 2.5",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ForecastConfigPayload(BaseModel):
    max_context: int = 512
    max_horizon: int = 32
    normalize_inputs: bool = True
    use_continuous_quantile_head: bool = True
    force_flip_invariance: bool = True
    infer_is_positive: bool = True
    fix_quantile_crossing: bool = True


class PredictRequest(BaseModel):
    series: list[list[float]] = Field(..., min_length=1, description="Batch of time-series (list of lists)")
    horizon: int = Field(default=12, ge=1, le=128, description="Forecast steps ahead")
    config: ForecastConfigPayload = Field(default_factory=ForecastConfigPayload)


class PredictResponse(BaseModel):
    forecast: list[list[float]]
    quantiles: list[list[list[float]]] | None = None
    method: str = "timesfm_2p5_torch"
    elapsed_ms: float = 0.0


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {
        "status": "ok" if _model is not None else "loading",
        "model": _MODEL_ID,
    }


@app.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest):
    if _model is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")

    try:
        import timesfm

        config = timesfm.ForecastConfig(
            max_context=req.config.max_context,
            max_horizon=req.config.max_horizon,
            normalize_inputs=req.config.normalize_inputs,
            use_continuous_quantile_head=req.config.use_continuous_quantile_head,
            force_flip_invariance=req.config.force_flip_invariance,
            infer_is_positive=req.config.infer_is_positive,
            fix_quantile_crossing=req.config.fix_quantile_crossing,
        )

        inputs = [np.array(s, dtype=np.float32) for s in req.series]
        _model.compile(config)

        t0 = time.perf_counter()
        point_forecast, quantile_forecast = _model.forecast(
            horizon=req.horizon,
            inputs=inputs,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000

        forecast_lists = [row.tolist() for row in point_forecast]
        quantile_lists = (
            [batch.tolist() for batch in quantile_forecast]
            if quantile_forecast is not None
            else None
        )

        return PredictResponse(
            forecast=forecast_lists,
            quantiles=quantile_lists,
            elapsed_ms=round(elapsed_ms, 1),
        )

    except Exception as exc:
        logger.exception("Forecast failed")
        raise HTTPException(status_code=500, detail=f"Forecast error: {str(exc)[:200]}")
