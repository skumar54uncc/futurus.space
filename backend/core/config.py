import warnings
from typing import Any

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    clerk_secret_key: str
    clerk_jwt_key: str = ""
    # SECURITY: Set to Clerk session JWT `aud` (Frontend API / instance URL) to enforce audience checks
    clerk_jwt_audience: str = ""

    llm_api_key: str
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model_tier1: str = "gpt-4o"
    llm_model_tier2: str = "gpt-4o-mini"

    zep_api_key: str

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

    # development | production — SECURITY: gates HSTS and strict startup checks
    environment: str = "development"

    max_cost_per_simulation_usd: float = 15.00
    backend_url: str = "http://localhost:8000"

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
            "ensemble": 5,
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

    @model_validator(mode="after")
    def validate_critical_settings(self) -> "Settings":
        # SECURITY: Fail fast in production when secrets are clearly placeholders
        if self.environment == "production":
            errs: list[str] = []
            if not self.database_url or len(self.database_url) < 12:
                errs.append("DATABASE_URL must be set")
            if not self.llm_api_key or len(self.llm_api_key) < 8:
                errs.append("LLM_API_KEY must be set")
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
