"""
Security headers and authentication middleware
"""
from typing import Optional

from fastapi import Request, Security, HTTPException
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware

from app.config.settings import settings
from app.exceptions import AuthenticationError
from app.utils.logger import get_logger

logger = get_logger(__name__)

# API Key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> Optional[str]:
    """
    Verify API key for protected endpoints
    In production, this should check against a database of valid keys
    """
    # Skip auth check if not configured
    if not settings.api_key_required:
        return None

    if not api_key:
        logger.warning("Request without API key")
        raise AuthenticationError("API key required")

    # Validate API key (in production, check against database)
    valid_keys = settings.api_keys.split(",") if settings.api_keys else []
    if api_key not in valid_keys:
        logger.warning(
            "Invalid API key",
            extra={"api_key_prefix": api_key[:8] + "..." if len(api_key) > 8 else api_key}
        )
        raise AuthenticationError("Invalid API key")

    return api_key


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response
