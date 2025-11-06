"""
Rate limiting middleware
Prevents abuse by limiting requests per IP/API key
"""
import time
from collections import defaultdict
from typing import Dict, Tuple

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.exceptions import RateLimitError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiter
    For production, consider using Redis-based rate limiting
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour

        # Store: {identifier: [(timestamp, count), ...]}
        self.request_counts: Dict[str, list] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Get identifier (IP address or API key)
        identifier = self._get_identifier(request)

        # Check rate limits
        current_time = time.time()
        self._clean_old_requests(identifier, current_time)

        minute_requests = self._count_requests_in_window(identifier, current_time, 60)
        hour_requests = self._count_requests_in_window(identifier, current_time, 3600)

        # Add rate limit headers
        remaining_minute = max(0, self.requests_per_minute - minute_requests)
        remaining_hour = max(0, self.requests_per_hour - hour_requests)

        if minute_requests >= self.requests_per_minute:
            logger.warning(
                f"Rate limit exceeded for {identifier} (per minute)",
                extra={
                    "identifier": identifier,
                    "requests": minute_requests,
                    "limit": self.requests_per_minute,
                    "window": "minute",
                }
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "message": "Rate limit exceeded (per minute)",
                        "retry_after": 60,
                    }
                },
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(current_time + 60)),
                    "Retry-After": "60",
                }
            )

        if hour_requests >= self.requests_per_hour:
            logger.warning(
                f"Rate limit exceeded for {identifier} (per hour)",
                extra={
                    "identifier": identifier,
                    "requests": hour_requests,
                    "limit": self.requests_per_hour,
                    "window": "hour",
                }
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "message": "Rate limit exceeded (per hour)",
                        "retry_after": 3600,
                    }
                },
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_hour),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(current_time + 3600)),
                    "Retry-After": "3600",
                }
            )

        # Record this request
        self.request_counts[identifier].append(current_time)

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(remaining_minute - 1)
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(remaining_hour - 1)

        return response

    def _get_identifier(self, request: Request) -> str:
        """Get identifier for rate limiting (API key or IP)"""
        # Try to get API key from header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"key:{api_key}"

        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return f"ip:{forwarded_for.split(',')[0].strip()}"

        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    def _clean_old_requests(self, identifier: str, current_time: float):
        """Remove requests older than 1 hour"""
        if identifier in self.request_counts:
            self.request_counts[identifier] = [
                ts for ts in self.request_counts[identifier]
                if current_time - ts < 3600
            ]

    def _count_requests_in_window(self, identifier: str, current_time: float, window: int) -> int:
        """Count requests within the specified time window (in seconds)"""
        if identifier not in self.request_counts:
            return 0

        return sum(
            1 for ts in self.request_counts[identifier]
            if current_time - ts < window
        )
