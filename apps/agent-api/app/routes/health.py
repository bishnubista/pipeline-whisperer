"""
Comprehensive health check endpoints
Provides readiness, liveness, and startup probes for Kubernetes
"""
import time
from datetime import datetime
from typing import Dict, Any

import httpx
from fastapi import APIRouter, status
from sqlalchemy import text

from app.config.settings import settings
from app.models.base import SessionLocal
from app.services.kafka_producer import get_kafka_producer
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/health", tags=["Health"])

# Track startup time
startup_time = time.time()


@router.get("/liveness", status_code=status.HTTP_200_OK)
async def liveness():
    """
    Liveness probe - indicates if the application is running
    Used by Kubernetes to determine if the container should be restarted
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": int(time.time() - startup_time),
    }


@router.get("/readiness", status_code=status.HTTP_200_OK)
async def readiness():
    """
    Readiness probe - indicates if the application is ready to serve traffic
    Used by Kubernetes to determine if traffic should be routed to this pod
    """
    checks = {}
    overall_healthy = True

    # Check database connection
    db_healthy = await _check_database()
    checks["database"] = {
        "status": "healthy" if db_healthy else "unhealthy",
        "required": True,
    }
    if not db_healthy:
        overall_healthy = False

    # Check Kafka connection
    kafka_healthy = await _check_kafka()
    checks["kafka"] = {
        "status": "healthy" if kafka_healthy else "unhealthy",
        "required": False,  # Not required for basic operation
    }

    # Check OpenAI service
    openai_healthy = await _check_openai()
    checks["openai"] = {
        "status": "healthy" if openai_healthy else "degraded",
        "required": False,  # Falls back to heuristic scoring
    }

    # Check Lightfield service
    lightfield_healthy = await _check_lightfield()
    checks["lightfield"] = {
        "status": "healthy" if lightfield_healthy else "degraded",
        "required": False,  # Falls back to simulation mode
    }

    response_status = status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if overall_healthy else "not_ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
    }


@router.get("/startup", status_code=status.HTTP_200_OK)
async def startup():
    """
    Startup probe - indicates if the application has started successfully
    Used by Kubernetes to know when the application is ready for liveness/readiness checks
    """
    # Check if minimum required time has passed (e.g., for initializations)
    min_startup_time = 5  # seconds
    elapsed = time.time() - startup_time

    if elapsed < min_startup_time:
        return {
            "status": "starting",
            "timestamp": datetime.utcnow().isoformat(),
            "elapsed_seconds": int(elapsed),
            "message": "Application is still initializing",
        }

    # Check if database is accessible
    db_healthy = await _check_database()

    if not db_healthy:
        return {
            "status": "starting",
            "timestamp": datetime.utcnow().isoformat(),
            "elapsed_seconds": int(elapsed),
            "message": "Waiting for database connection",
        }

    return {
        "status": "started",
        "timestamp": datetime.utcnow().isoformat(),
        "elapsed_seconds": int(elapsed),
    }


@router.get("/detailed", status_code=status.HTTP_200_OK)
async def detailed_health():
    """
    Detailed health check with comprehensive system information
    """
    checks = {}

    # Database check
    db_result = await _check_database_detailed()
    checks["database"] = db_result

    # Kafka check
    kafka_result = await _check_kafka_detailed()
    checks["kafka"] = kafka_result

    # OpenAI check
    openai_result = await _check_openai_detailed()
    checks["openai"] = openai_result

    # Lightfield check
    lightfield_result = await _check_lightfield_detailed()
    checks["lightfield"] = lightfield_result

    # System information
    system_info = {
        "uptime_seconds": int(time.time() - startup_time),
        "environment": settings.sentry_environment,
        "version": "0.2.0",
        "demo_mode": settings.demo_mode,
    }

    # Determine overall health
    critical_services = ["database"]
    overall_healthy = all(
        checks[service]["status"] == "healthy"
        for service in critical_services
        if service in checks
    )

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "system": system_info,
        "checks": checks,
    }


# Helper functions

async def _check_database() -> bool:
    """Quick database health check"""
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return False


async def _check_database_detailed() -> Dict[str, Any]:
    """Detailed database health check"""
    try:
        db = SessionLocal()
        start_time = time.time()
        result = db.execute(text("SELECT 1"))
        latency_ms = int((time.time() - start_time) * 1000)
        db.close()

        return {
            "status": "healthy",
            "latency_ms": latency_ms,
            "url": settings.database_url.split("@")[-1] if "@" in settings.database_url else "sqlite",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


async def _check_kafka() -> bool:
    """Quick Kafka health check"""
    try:
        producer = get_kafka_producer()
        # Just check if producer is available
        return producer is not None
    except Exception as e:
        logger.warning(f"Kafka health check failed: {e}")
        return False


async def _check_kafka_detailed() -> Dict[str, Any]:
    """Detailed Kafka health check"""
    try:
        producer = get_kafka_producer()
        if producer is None:
            return {
                "status": "degraded",
                "message": "Kafka producer not initialized (demo mode)",
            }

        return {
            "status": "healthy",
            "brokers": settings.redpanda_brokers,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


async def _check_openai() -> bool:
    """Quick OpenAI health check"""
    if not settings.openai_api_key:
        return False

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.openai_base_url}/models",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"}
            )
            return response.status_code == 200
    except Exception:
        return False


async def _check_openai_detailed() -> Dict[str, Any]:
    """Detailed OpenAI health check"""
    if not settings.openai_api_key:
        return {
            "status": "degraded",
            "message": "OpenAI API key not configured (using fallback scoring)",
        }

    try:
        start_time = time.time()
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.openai_base_url}/models",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"}
            )
            latency_ms = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "latency_ms": latency_ms,
                    "model": settings.openai_model,
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}",
                }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


async def _check_lightfield() -> bool:
    """Quick Lightfield health check"""
    if not settings.lightfield_api_key or settings.simulate_lightfield:
        return False

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.lightfield_base_url}/health",
                headers={"Authorization": f"Bearer {settings.lightfield_api_key}"}
            )
            return response.status_code == 200
    except Exception:
        return False


async def _check_lightfield_detailed() -> Dict[str, Any]:
    """Detailed Lightfield health check"""
    if not settings.lightfield_api_key or settings.simulate_lightfield:
        return {
            "status": "degraded",
            "message": "Lightfield API key not configured or simulation mode enabled",
        }

    try:
        start_time = time.time()
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.lightfield_base_url}/health",
                headers={"Authorization": f"Bearer {settings.lightfield_api_key}"}
            )
            latency_ms = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "latency_ms": latency_ms,
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}",
                }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }
