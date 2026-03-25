import time

import httpx
from jose import jwt, JWTError
from core.config import settings
import structlog

logger = structlog.get_logger()

CLERK_JWKS_URL = "https://api.clerk.com/v1/jwks"

# SECURITY: JWKS cache with TTL so key rotation is picked up
_jwks_cache: dict | None = None
_jwks_cache_time: float = 0.0
_JWKS_TTL_SECONDS = 3600


async def get_clerk_jwks() -> dict:
    global _jwks_cache, _jwks_cache_time
    now = time.time()
    if _jwks_cache is not None and (now - _jwks_cache_time) < _JWKS_TTL_SECONDS:
        return _jwks_cache

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            CLERK_JWKS_URL,
            headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
        )
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_cache_time = now
        return _jwks_cache


async def verify_clerk_token(token: str) -> dict:
    """Verify a Clerk JWT and return the payload (claims)."""
    try:
        jwks = await get_clerk_jwks()
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        key = None
        for k in jwks.get("keys", []):
            if k["kid"] == kid:
                key = k
                break

        if not key:
            raise JWTError("No matching key found in JWKS")

        # SECURITY: Enforce audience when configured (production / hardened setups)
        verify_aud = bool(settings.clerk_jwt_audience)
        decode_kwargs: dict = {
            "algorithms": ["RS256"],
            "options": {
                "verify_aud": verify_aud,
                "verify_exp": True,
            },
        }
        if verify_aud:
            decode_kwargs["audience"] = settings.clerk_jwt_audience

        payload = jwt.decode(token, key, **decode_kwargs)
        return payload
    except JWTError as e:
        logger.warning("jwt_verification_failed", error=str(e))
        raise
