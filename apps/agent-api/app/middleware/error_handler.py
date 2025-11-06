"""
Error handling middleware for FastAPI
Provides structured error responses and logging
"""
import traceback
import uuid
from typing import Any, Dict

import sentry_sdk
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.exceptions import PipelineWhispererException
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware to catch and handle all exceptions"""

    async def dispatch(self, request: Request, call_next):
        # Generate correlation ID for request tracking
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = correlation_id
            return response

        except PipelineWhispererException as exc:
            # Handle custom application exceptions
            logger.warning(
                f"Application error: {exc.message}",
                extra={
                    "correlation_id": correlation_id,
                    "status_code": exc.status_code,
                    "details": exc.details,
                    "path": request.url.path,
                    "method": request.method,
                }
            )

            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": {
                        "message": exc.message,
                        "details": exc.details,
                        "correlation_id": correlation_id,
                        "type": exc.__class__.__name__,
                    }
                },
                headers={"X-Correlation-ID": correlation_id}
            )

        except Exception as exc:
            # Handle unexpected exceptions
            logger.error(
                f"Unexpected error: {str(exc)}",
                extra={
                    "correlation_id": correlation_id,
                    "traceback": traceback.format_exc(),
                    "path": request.url.path,
                    "method": request.method,
                },
                exc_info=True
            )

            # Report to Sentry
            with sentry_sdk.push_scope() as scope:
                scope.set_context("request", {
                    "url": str(request.url),
                    "method": request.method,
                    "headers": dict(request.headers),
                })
                scope.set_tag("correlation_id", correlation_id)
                sentry_sdk.capture_exception(exc)

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "message": "An unexpected error occurred",
                        "correlation_id": correlation_id,
                        "type": "InternalServerError",
                    }
                },
                headers={"X-Correlation-ID": correlation_id}
            )
