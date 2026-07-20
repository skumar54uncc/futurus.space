import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIASGIMiddleware
from sqlalchemy import select
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.config import settings

_shared_processors = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.add_log_level,
]
if settings.environment == "development":
    structlog.configure(
        processors=_shared_processors + [structlog.dev.ConsoleRenderer(colors=True)],
        wrapper_class=structlog.make_filtering_bound_logger(20),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
else:
    structlog.configure(
        processors=_shared_processors + [structlog.processors.JSONRenderer()],
        wrapper_class=structlog.make_filtering_bound_logger(20),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

if settings.sentry_dsn:
    import logging

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    def _scrub_pii(event, hint):
        if "request" in event:
            hdrs = event["request"].get("headers", {})
            if isinstance(hdrs, dict):
                for key in list(hdrs.keys()):
                    if key.lower() in ("authorization", "cookie", "x-api-key"):
                        hdrs[key] = "[Filtered]"
        return event

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        traces_sample_rate=0.05,
        send_default_pii=False,
        before_send=_scrub_pii,
    )

logger = structlog.get_logger()

from api.middleware.auth import get_current_user
from api.middleware.cost_guard import CostGuardMiddleware
from api.middleware.rate_limiter import limiter, rate_limit_exceeded_handler
from api.middleware.request_id import RequestIDMiddleware
from api.middleware.security_headers import SecurityHeadersMiddleware
from api.routes import auth, chat, ideas, reports, simulations
from core.database import AsyncSessionLocal, Base, engine
from core.redis import clear_upstash_client_cache, close_redis, get_redis
from core.security import verify_clerk_token
from models.simulation import Simulation
from models.user import User


async def _recover_stale_queued_simulations() -> None:
    """
    On startup, mark abandoned simulations FAILED so the dashboard does not spin forever.

    Cloud Run + inline workers: reap by *lease*, not by created_at alone.
    A healthy long-running sim keeps last_heartbeat_at fresh and survives cold starts
    on other instances. A dead worker stops heartbeating and is reaped after LEASE_SECONDS.

    Celery mode: fail any active status immediately (worker process is gone).
    """
    from datetime import datetime, timedelta, timezone

    from models.simulation import SimulationStatus
    from services.simulation_recovery import (
        ACTIVE_STATUSES,
        LEASE_SECONDS,
        QUEUED_MAX_AGE,
    )
    from sqlalchemy import func, update

    async with AsyncSessionLocal() as db:
        from models.simulation import Simulation

        if settings.simulation_worker_inline:
            now = datetime.now(timezone.utc)
            queued_cutoff = now - QUEUED_MAX_AGE
            lease_cutoff = now - timedelta(seconds=LEASE_SECONDS)

            result = await db.execute(
                update(Simulation)
                .where(
                    Simulation.status == SimulationStatus.QUEUED,
                    Simulation.created_at < queued_cutoff,
                )
                .values(
                    status=SimulationStatus.FAILED,
                    error_message=(
                        "Run was stuck in queue too long and was cleared. "
                        "Please start a new simulation."
                    ),
                )
                .returning(Simulation.id)
            )
            # Coalesce heartbeat → started_at → created_at so pre-migration rows still reap.
            effective_hb = func.coalesce(
                Simulation.last_heartbeat_at,
                Simulation.started_at,
                Simulation.created_at,
            )
            stale_active = await db.execute(
                update(Simulation)
                .where(
                    Simulation.status.in_(ACTIVE_STATUSES),
                    effective_hb < lease_cutoff,
                )
                .values(
                    status=SimulationStatus.FAILED,
                    error_message=(
                        "Run lost its worker lease (no heartbeat). "
                        "Please start a new simulation."
                    ),
                )
                .returning(Simulation.id)
            )
            recovered = list(result.fetchall()) + list(stale_active.fetchall())
            await db.commit()
            if recovered:
                logger.warning(
                    "stale_simulations_terminated_on_startup",
                    count=len(recovered),
                    ids=[str(r[0]) for r in recovered],
                    mode="inline_lease",
                    lease_seconds=LEASE_SECONDS,
                )
            return

        # Celery / dedicated worker: prior process is gone — fail all active.
        _STALE_STATUSES = (
            SimulationStatus.QUEUED,
            SimulationStatus.BUILDING_SEED,
            SimulationStatus.GENERATING_PERSONAS,
            SimulationStatus.RUNNING,
            SimulationStatus.GENERATING_REPORT,
        )
        result = await db.execute(
            update(Simulation)
            .where(Simulation.status.in_(_STALE_STATUSES))
            .values(
                status=SimulationStatus.FAILED,
                error_message="Run was interrupted — server restarted. Please start a new simulation.",
            )
            .returning(Simulation.id)
        )
        recovered = result.fetchall()
        await db.commit()
        if recovered:
            logger.warning(
                "stale_simulations_terminated_on_startup",
                count=len(recovered),
                ids=[str(r[0]) for r in recovered],
                mode="celery_immediate",
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "futurus_starting",
        environment=settings.environment,
        simulation_worker_inline=settings.simulation_worker_inline,
    )
    if not settings.simulation_worker_inline:
        logger.warning(
            "simulation_worker_inline_disabled",
            hint="New simulations are sent to Celery only. Without a worker process they stay queued. "
            "Run: celery -A workers.celery_app worker -l info — or set FUTURUS_SIMULATION_WORKER_INLINE=true in .env",
        )
    if settings.environment == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("dev_schema_synced")
    else:
        logger.info("production_schema_managed_by_alembic")

    # Idempotent column additions — safe to run on every startup (ADD COLUMN IF NOT EXISTS).
    # Add new nullable columns here instead of a full Alembic revision when the column has a safe default.
    from sqlalchemy import text
    _SAFE_MIGRATIONS = [
        "ALTER TABLE reports ADD COLUMN IF NOT EXISTS citations JSONB DEFAULT '[]'",
        "ALTER TABLE simulations ADD COLUMN IF NOT EXISTS llm_usage JSONB DEFAULT NULL",
        "ALTER TABLE simulations ADD COLUMN IF NOT EXISTS last_heartbeat_at TIMESTAMPTZ DEFAULT NULL",
    ]
    async with engine.begin() as conn:
        for stmt in _SAFE_MIGRATIONS:
            await conn.execute(text(stmt))
    logger.info("safe_column_migrations_applied")

    await _recover_stale_queued_simulations()

    # Warm up remote TimesFM service (HF Space free tier sleeps after ~15 min).
    # Non-blocking: if it fails, first real forecast will just be slower.
    from services.timesfm_client import warmup_timesfm
    await warmup_timesfm()

    yield

    logger.info("futurus_shutting_down")
    from services.llm_router import cleanup_http_client
    await cleanup_http_client()
    await engine.dispose()
    await close_redis()
    clear_upstash_client_cache()
    logger.info("futurus_shutdown_complete")


app = FastAPI(
    title="Futurus API",
    description="Startup Fate Simulator — powered by MiroFish",
    version="1.0.0",
    lifespan=lifespan,
)

# SECURITY: Rate limits (SlowAPI)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
# SlowAPIASGIMiddleware avoids BaseHTTPMiddleware + _inject_headers isinstance bug
# ("response must be an instance of starlette.responses.Response") seen with SlowAPIMiddleware
# when headers_enabled=True and other BaseHTTPMiddleware wrap the stack.
app.add_middleware(SlowAPIASGIMiddleware)

# SECURITY: Browser-oriented headers on API responses
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)

# CORS: futurus.dev + CORS_EXTRA_ORIGINS; regex always allows local dev and any *.vercel.app preview.
# (Previously Vercel previews only matched when ENVIRONMENT=production, so a missing env on DO blocked all previews.)
_dev_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
_prod_origins = [
    "https://futurus.dev",
    "https://www.futurus.dev",
]
_extra = [o.strip() for o in (settings.cors_extra_origins or "").split(",") if o.strip()]

_CORS_ORIGIN_REGEX = (
    r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
    r"|"
    r"^https://[a-zA-Z0-9][a-zA-Z0-9._-]*\.vercel\.app$"
    r"|"
    r"^https://([a-zA-Z0-9-]+\.)?futurus\.dev$"
)

app.add_middleware(CostGuardMiddleware)

# Keep CORS as the outermost middleware so even early errors still include CORS headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_prod_origins + _extra + (_dev_origins if settings.environment != "production" else []),
    allow_origin_regex=_CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def request_validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # SECURITY: Never leak stack traces or internals to clients
    if isinstance(exc, StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    logger.exception(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."},
    )


@app.websocket("/ws/simulation/{simulation_id}")
async def simulation_websocket(websocket: WebSocket, simulation_id: str):
    """
    SECURITY: Clerk JWT via ?token= (browsers cannot set WS Authorization headers).
    Ownership verified before subscribe.
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        return

    try:
        payload = await verify_clerk_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=1008, reason="Invalid token")
            return
    except Exception:
        await websocket.close(code=1008, reason="Invalid or expired token")
        return

    try:
        sim_uuid = uuid.UUID(simulation_id)
    except ValueError:
        await websocket.close(code=1008, reason="Invalid simulation ID")
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Simulation).where(
                Simulation.id == sim_uuid,
                Simulation.user_id == user_id,
            )
        )
        sim = result.scalar_one_or_none()
        if not sim:
            await websocket.close(code=1008, reason="Simulation not found or access denied")
            return

    await websocket.accept()
    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(f"sim:{simulation_id}")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                # SECURITY: Never forward raw internal errors to the client
                if data.get("progress") == -1:
                    data["message"] = "Simulation encountered an error. Please try again."
                    data.pop("error_detail", None)
                await websocket.send_json(data)
                if data.get("progress") in (-1, 100):
                    break
    except Exception as e:
        logger.warning(
            "websocket_error",
            simulation_id=simulation_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Connection interrupted. Please refresh.",
                "progress": -1,
            })
        except Exception:
            pass  # Client already disconnected — acceptable here
    finally:
        await pubsub.unsubscribe(f"sim:{simulation_id}")
        await pubsub.aclose()
        # Connection returned to pool — do not close the shared client.


app.include_router(auth.router)
app.include_router(simulations.router)
app.include_router(reports.router)
app.include_router(chat.router)
app.include_router(ideas.router)


static_dir = Path(__file__).parent / "static" / "reports"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/reports", StaticFiles(directory=str(static_dir)), name="reports")


@app.get("/health")
@limiter.exempt
async def health(request: Request):
    checks: dict[str, str] = {"api": "ok"}

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(select(1))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
        logger.error("health_db_failed", exc_info=True)

    try:
        r = await get_redis()
        await r.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"
        logger.error("health_redis_failed", exc_info=True)

    all_ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        content={
            "status": "ok" if all_ok else "degraded",
            "service": "futurus-api",
            "checks": checks,
        },
        status_code=200 if all_ok else 503,
    )


@app.get("/api/admin/llm-status")
async def llm_status(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    SECURITY: LLM provider status — admin email (production) or enterprise tier when unset.
    """
    admin = (settings.admin_email or "").strip().lower()
    if admin:
        if (current_user.email or "").strip().lower() != admin:
            raise HTTPException(status_code=403, detail="Admin access required")
    elif current_user.plan_tier != "enterprise":
        raise HTTPException(status_code=403, detail="Admin access required")

    from services.llm_router import get_providers
    from services.cost_tracker import get_usage_snapshot
    from services.timesfm_client import is_remote_enabled

    rows = get_providers()
    return {
        "providers": [
            {
                "name": x["name"],
                "model": x.get("model"),
                "available": x["available"],
                "keys_count": len(x.get("keys", [])),
            }
            for x in rows
        ],
        "usage": get_usage_snapshot(),
        "validators": {
            "timesfm_remote": is_remote_enabled(),
            "timesfm_service_url_set": bool((settings.timesfm_service_url or "").strip()),
            "tavily_set": bool((settings.tavily_api_key or "").strip()),
            "note": (
                "TimesFM uses HF Space when TIMESFM_SERVICE_URL is set; else heuristic. "
                "MIRAI-lite uses Tavily when TAVILY_API_KEY is set; else default macro shocks."
            ),
        },
    }
