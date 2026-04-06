import warnings
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings
from functools import lru_cache


def _strip_sslmode_for_asyncpg(url: str) -> str:
    """
    asyncpg does not accept libpq's sslmode= query param (TypeError: unexpected keyword sslmode).
    Map common sslmode values to asyncpg's ssl= query param.
    """
    if "sslmode" not in url.lower():
        return url
    parsed = urlparse(url)
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    new_pairs: list[tuple[str, str]] = []
    sslmode_effect: str | None = None
    for k, v in pairs:
        if k.lower() == "sslmode":
            vl = v.lower()
            if vl == "disable":
                sslmode_effect = "off"
            elif vl in ("require", "verify-ca", "verify-full", "prefer", "allow"):
                sslmode_effect = "on"
            continue
        new_pairs.append((k, v))
    has_ssl = any(x[0].lower() == "ssl" for x in new_pairs)
    if not has_ssl:
        if sslmode_effect == "on":
            new_pairs.append(("ssl", "true"))
        elif sslmode_effect == "off":
            new_pairs.append(("ssl", "false"))
    new_query = urlencode(new_pairs)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))


class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    # Cap asyncio Redis pool (WebSocket pub/sub, health, idempotency). Upstash free tier: ~20 TCP connections total.
    redis_max_connections: int = Field(
        default=8,
        validation_alias=AliasChoices(
            "FUTURUS_REDIS_MAX_CONNECTIONS",
            "REDIS_MAX_CONNECTIONS",
        ),
    )

    # Upstash REST (HTTP) — optional LLM counters; no persistent TCP. Prefer with Upstash free tier.
    upstash_redis_rest_url: str = Field(
        default="",
        validation_alias=AliasChoices("UPSTASH_REDIS_REST_URL"),
    )
    upstash_redis_rest_token: str = Field(
        default="",
        validation_alias=AliasChoices("UPSTASH_REDIS_REST_TOKEN"),
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url_for_asyncpg(cls, v: Any) -> Any:
        """
        Supabase and others default to postgresql://… — SQLAlchemy then picks the sync
        psycopg2 dialect (ModuleNotFoundError without psycopg2). Futurus uses asyncpg only.
        Strip sslmode=… — asyncpg rejects it; use ssl=true|false instead.
        """
        if not isinstance(v, str):
            return v
        s = v.strip()
        if "://" not in s:
            return v
        scheme, rest = s.split("://", 1)
        scheme_l = scheme.lower()
        if scheme_l in ("postgres", "postgresql"):
            s = f"postgresql+asyncpg://{rest}"
        elif scheme_l == "postgresql+asyncpg":
            s = f"postgresql+asyncpg://{rest}"
        if s.startswith("postgresql+asyncpg://"):
            s = _strip_sslmode_for_asyncpg(s)
        return s

    @field_validator("redis_url", mode="before")
    @classmethod
    def normalize_redis_url(cls, v: Any) -> Any:
        """
        SlowAPI/limits expects a URI (redis:// or rediss://), not `redis-cli --tls -u ...`.
        Upstash TLS endpoints should use rediss:// for redis-py.
        """
        if not isinstance(v, str):
            return v
        s = v.strip()
        if "rediss://" in s:
            idx = s.index("rediss://")
            s = s[idx:].strip().split()[0]
            return s
        if "redis://" in s:
            idx = s.index("redis://")
            s = s[idx:].strip().split()[0]
            if "upstash.io" in s.lower():
                return "rediss://" + s[len("redis://") :]
            return s
        return s

    clerk_secret_key: str
    clerk_jwt_key: str = ""
    # SECURITY: Set to Clerk session JWT `aud` (Frontend API / instance URL) to enforce audience checks
    clerk_jwt_audience: str = ""

    # Legacy single-key (kept for backward compat; new code uses llm_router)
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model_tier1: str = "gpt-4o"
    llm_model_tier2: str = "gpt-4o-mini"

    # ── Multi-provider LLM keys ───────────────────────────────────────────────
    groq_api_keys: str = ""          # comma-separated list of up to 7 keys
    gemini_api_key: str = ""
    openrouter_api_key: str = ""

    # DigitalOcean Gradient serverless inference (OpenAI-compatible /v1/chat/completions)
    digitalocean_model_access_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "DIGITALOCEAN_MODEL_ACCESS_KEY",
            "MODEL_ACCESS_KEY",
        ),
    )
    digitalocean_inference_base_url: str = Field(
        default="https://inference.do-ai.run/v1",
        validation_alias=AliasChoices("DIGITALOCEAN_INFERENCE_BASE_URL"),
    )

    # ── Agent tier config ─────────────────────────────────────────────────────
    agent_tier1_count: int = 50      # agents that get full LLM every turn
    agent_tier2_count: int = 200     # agents that get LLM every 4 turns
    # remaining agents = Tier 3, probabilistic only

    tavily_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("TAVILY_API_KEY"),
    )

    zep_api_key: str = ""

    s3_bucket: str = Field(default="futurus-reports", validation_alias=AliasChoices("S3_BUCKET"))
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_endpoint_url: str = ""

    aws_access_key_id: str = Field(
        default="",
        validation_alias=AliasChoices("AWS_ACCESS_KEY_ID", "S3_ACCESS_KEY", "AWS_ACCESS_KEY"),
    )
    aws_secret_access_key: str = Field(
        default="",
        validation_alias=AliasChoices("AWS_SECRET_ACCESS_KEY", "S3_SECRET_KEY", "AWS_SECRET_KEY"),
    )
    aws_region: str = Field(default="us-east-1", validation_alias=AliasChoices("AWS_REGION", "S3_REGION"))
    aws_s3_bucket: str = Field(
        default="futurus-reports",
        validation_alias=AliasChoices("AWS_S3_BUCKET"),
    )
    aws_cloudfront_url: str = Field(default="", validation_alias=AliasChoices("AWS_CLOUDFRONT_URL", "CLOUDFRONT_URL"))
    aws_ses_region: str = "us-east-1"
    app_domain: str = "futurus.dev"

    # Optional SMTP (e.g. Gmail app password on DigitalOcean). Used for simulation-complete email when SES fails or is unset.
    # Same variable names as Vercel contact form: SMTP_HOST, SMTP_USER, SMTP_PASS.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = Field(
        default="",
        validation_alias=AliasChoices("SMTP_PASS", "SMTP_PASSWORD"),
    )
    smtp_from: str = ""
    # Set true for port 465 (SMTPS). Port 587 uses STARTTLS automatically.
    smtp_secure: bool = False

    # development | production — SECURITY: gates HSTS and strict startup checks
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "FUTURUS_ENVIRONMENT"),
    )

    sentry_dsn: str = Field(
        default="",
        validation_alias=AliasChoices("SENTRY_DSN", "FUTURUS_SENTRY_DSN"),
    )
    # Restrict /api/admin/llm-status; falls back to enterprise tier if unset (see main.py).
    admin_email: str = Field(
        default="",
        validation_alias=AliasChoices("ADMIN_EMAIL", "FUTURUS_ADMIN_EMAIL"),
    )

    max_cost_per_simulation_usd: float = 3.00
    backend_url: str = "http://localhost:8000"

    # Comma-separated extra CORS origins for production (e.g. https://myapp.vercel.app)
    cors_extra_origins: str = ""

    # SlowAPI storage: empty → use redis_url. "memory" / "memory://" → in-process (no sync Redis hop per request).
    # Use memory on a single App Platform instance to avoid blocking the asyncio loop on Upstash latency.
    # For multiple replicas, keep default (Redis) so limits are shared.
    rate_limit_storage_uri: str = Field(
        default="",
        validation_alias=AliasChoices(
            "FUTURUS_RATE_LIMIT_STORAGE_URI",
            "FUTURUS_RATE_LIMIT_STORAGE",
            "RATE_LIMIT_STORAGE_URI",
        ),
    )

    # Idea analysis LLM bounds — keep total under ~55s so strict gateways (60s) return JSON instead of 504.
    idea_analysis_total_deadline_seconds: float = Field(
        default=52.0,
        validation_alias=AliasChoices("FUTURUS_IDEA_ANALYSIS_DEADLINE_SECONDS"),
    )
    idea_analysis_llm_read_timeout_seconds: float = Field(
        default=22.0,
        validation_alias=AliasChoices("FUTURUS_IDEA_ANALYSIS_READ_TIMEOUT"),
    )
    idea_analysis_max_provider_attempts: int = Field(
        default=4,
        validation_alias=AliasChoices("FUTURUS_IDEA_ANALYSIS_MAX_PROVIDERS"),
    )

    persona_generation_total_deadline_seconds: float = Field(
        default=55.0,
        validation_alias=AliasChoices("FUTURUS_PERSONA_GENERATION_DEADLINE_SECONDS"),
    )
    persona_generation_llm_read_timeout_seconds: float = Field(
        default=24.0,
        validation_alias=AliasChoices("FUTURUS_PERSONA_READ_TIMEOUT"),
    )

    # Per-turn engine timeout (seconds) before skipping a stuck turn.
    mirofish_step_timeout_seconds: float = Field(
        default=120.0,
        validation_alias=AliasChoices("MIROFISH_STEP_TIMEOUT", "FUTURUS_MIROFISH_STEP_TIMEOUT"),
    )

    # Commit simulation turn updates every N turns to reduce DB write pressure.
    simulation_turn_commit_interval: int = Field(
        default=2,
        validation_alias=AliasChoices(
            "FUTURUS_SIM_TURN_COMMIT_INTERVAL",
            "SIM_TURN_COMMIT_INTERVAL",
        ),
    )

    # If True, run simulations in a daemon thread (no Celery/Redis worker required).
    # Default True so local dev works with `uvicorn` only. Set false in production when using Celery.
    simulation_worker_inline: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "FUTURUS_SIMULATION_WORKER_INLINE", "SIMULATION_WORKER_INLINE"
        ),
    )

    # Single cap for all signed-in users (no billing tiers). Tune as needed.
    simulation_limits: dict[str, Any] = Field(
        default_factory=lambda: {
            "agents": 1000,
            "turns": 40,
            "ensemble": 1,
        }
    )

    # SECURITY: Monthly simulation quotas by plan_tier (user.plan_tier). -1 = unlimited.
    plan_limits: dict[str, dict[str, int]] = Field(
        default_factory=lambda: {
            "free": {"sims_per_month": 3},
            "open": {"sims_per_month": 20},
            "pro": {"sims_per_month": 50},
            "enterprise": {"sims_per_month": -1},
        }
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

    @model_validator(mode="after")
    def fill_aws_from_legacy_s3_fields(self) -> "Settings":
        if not self.aws_access_key_id and self.s3_access_key:
            object.__setattr__(self, "aws_access_key_id", self.s3_access_key)
        if not self.aws_secret_access_key and self.s3_secret_key:
            object.__setattr__(self, "aws_secret_access_key", self.s3_secret_key)
        awb = (self.aws_s3_bucket or "").strip()
        sb = (self.s3_bucket or "").strip()
        merged_bucket = awb or sb or "futurus-reports"
        object.__setattr__(self, "aws_s3_bucket", merged_bucket)
        object.__setattr__(self, "s3_bucket", merged_bucket)
        return self

    def openai_compatible_llm_key(self) -> str:
        """Bearer token for OpenAI-compatible APIs (DO Gradient, OpenAI, Groq-style passthrough)."""
        return (self.digitalocean_model_access_key or self.llm_api_key or "").strip()

    def openai_compatible_llm_base(self) -> str:
        """Base URL without trailing slash (…/v1/chat/completions is appended by clients)."""
        if (self.digitalocean_model_access_key or "").strip():
            return self.digitalocean_inference_base_url.rstrip("/")
        return (self.llm_base_url or "https://api.openai.com/v1").rstrip("/")

    @model_validator(mode="after")
    def validate_critical_settings(self) -> "Settings":
        # SECURITY: Fail fast in production when secrets are clearly placeholders
        if self.environment == "production":
            errs: list[str] = []
            if not self.database_url or len(self.database_url) < 12:
                errs.append("DATABASE_URL must be set")
            has_any_llm_key = (
                (self.llm_api_key and len(self.llm_api_key) >= 8)
                or bool((self.digitalocean_model_access_key or "").strip())
                or bool(self.groq_api_keys.strip())
                or bool(self.gemini_api_key.strip())
                or bool(self.openrouter_api_key.strip())
            )
            if not has_any_llm_key:
                errs.append(
                    "At least one LLM key must be set (MODEL_ACCESS_KEY / DIGITALOCEAN_MODEL_ACCESS_KEY, "
                    "LLM_API_KEY, GROQ_API_KEYS, GEMINI_API_KEY, or OPENROUTER_API_KEY)"
                )
            if not self.clerk_secret_key or len(self.clerk_secret_key) < 20:
                errs.append("CLERK_SECRET_KEY must be set")
            if not self.clerk_jwt_audience:
                errs.append("CLERK_JWT_AUDIENCE must be set in production for JWT audience verification")
            if errs:
                raise ValueError("Configuration errors: " + "; ".join(errs))

        if self.max_cost_per_simulation_usd > 10.0:
            warnings.warn(
                f"MAX_COST_PER_SIMULATION_USD={self.max_cost_per_simulation_usd} is high; "
                "consider ≤10 for tighter LLM spend control.",
                stacklevel=2,
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
