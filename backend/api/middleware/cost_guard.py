"""Per-request LLM cost tracking middleware."""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
import structlog

logger = structlog.get_logger()


class CostGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        request.state.llm_cost_usd = 0.0
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "costguard_unhandled_exception",
                path=request.url.path,
                method=request.method,
            )
            raise
        duration_ms = (time.monotonic() - start) * 1000

        cost = getattr(request.state, "llm_cost_usd", 0.0)
        if cost > 0:
            logger.info(
                "request_llm_cost",
                path=request.url.path,
                cost_usd=cost,
                duration_ms=round(duration_ms, 1),
            )

        return response
