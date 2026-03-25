"""
SECURITY: Security headers on API responses (defense in depth for any HTML/static).
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # SECURITY: Clickjacking protection
        response.headers["X-Frame-Options"] = "DENY"
        # SECURITY: MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # SECURITY: Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # SECURITY: Restrict powerful features
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        # SECURITY: HSTS only when explicitly production + HTTPS (avoid local dev breakage)
        if settings.environment == "production" and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # SECURITY: Minimal CSP for this JSON API (browsers apply to any HTML error pages)
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
        )

        # Starlette MutableHeaders has no .pop(); strip Server if Uvicorn added it.
        if "server" in response.headers:
            del response.headers["server"]
        return response
