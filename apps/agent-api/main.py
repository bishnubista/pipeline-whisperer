"""
Pipeline Whisperer Agent API
Production-ready FastAPI application with comprehensive middleware
"""
import signal
import sys
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import func

from app.config.settings import settings
from app.routes import leads_router
from app.routes.experiments import router as experiments_router
from app.routes.dashboard import router as dashboard_router
from app.routes.health import router as health_router
from app.models.base import SessionLocal, engine
from app.models.lead import Lead
from app.middleware import ErrorHandlerMiddleware, RateLimiterMiddleware, SecurityHeadersMiddleware
from app.utils.logger import configure_logging, get_logger
from app.services.cache import get_redis_client

# Configure structured logging
configure_logging()
logger = get_logger(__name__)

# Initialize Sentry (only if DSN is configured and valid)
if settings.sentry_dsn_python and not settings.sentry_dsn_python.startswith("https://your_"):
    sentry_sdk.init(
        dsn=settings.sentry_dsn_python,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        profiles_sample_rate=settings.sentry_profiles_sample_rate,
        environment=settings.sentry_environment,
    )
    logger.info("Sentry monitoring enabled", extra={"environment": settings.sentry_environment})
else:
    logger.info("Sentry monitoring disabled (DSN not configured)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events with graceful handling"""
    # Startup
    logger.info("Pipeline Whisperer Agent API starting...", extra={
        "version": "0.2.0",
        "environment": settings.sentry_environment,
        "demo_mode": settings.demo_mode,
    })

    # Initialize Redis client
    if settings.redis_enabled:
        redis_client = get_redis_client()
        if redis_client:
            logger.info("Redis cache initialized")
        else:
            logger.warning("Redis initialization failed, caching disabled")

    # Verify database connection
    try:
        db = SessionLocal()
        db.execute(func.text("SELECT 1"))
        db.close()
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")

    # Register graceful shutdown handlers
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, initiating graceful shutdown...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    yield

    # Shutdown
    logger.info("Pipeline Whisperer Agent API shutting down...")

    # Cleanup database connections
    try:
        engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")

    logger.info("Shutdown complete")


app = FastAPI(
    title="Pipeline Whisperer Agent API",
    description="Production-ready autonomous GTM agent powered by Lightfield, OpenAI, Redpanda, Truefoundry, and Sentry",
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.demo_mode else "/docs",
    redoc_url="/redoc" if not settings.demo_mode else "/redoc",
)

# Add middleware (order matters - first added is outermost)
# 1. Security headers (outermost)
app.add_middleware(SecurityHeadersMiddleware)

# 2. GZIP compression
if settings.enable_compression:
    app.add_middleware(GZipMiddleware, minimum_size=1000)

# 3. CORS
cors_origins = settings.cors_origins.split(",") if settings.cors_origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Rate limiting
app.add_middleware(
    RateLimiterMiddleware,
    requests_per_minute=settings.rate_limit_per_minute,
    requests_per_hour=settings.rate_limit_per_hour,
)

# 5. Error handler (innermost - catches all errors)
app.add_middleware(ErrorHandlerMiddleware)

# Include routers
app.include_router(health_router)  # Health checks
app.include_router(leads_router)
app.include_router(experiments_router)
app.include_router(dashboard_router)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Pipeline Whisperer Agent API",
        "version": "0.2.0",
        "status": "running",
        "environment": settings.sentry_environment,
        "docs": "/docs",
        "health": "/health/detailed",
    }


@app.get("/metrics")
async def metrics():
    """Metrics endpoint with system information"""
    from app.models.base import get_db_pool_status
    from app.services.cache import get_cache_stats

    db = SessionLocal()
    try:
        total_leads = db.query(func.count(Lead.id)).scalar() or 0
        scored_leads = db.query(func.count(Lead.id)).filter(Lead.score.isnot(None)).scalar() or 0
        avg_score = db.query(func.avg(Lead.score)).scalar() or 0.0

        return {
            "leads": {
                "total": total_leads,
                "scored": scored_leads,
                "avg_score": round(avg_score, 3),
            },
            "database": get_db_pool_status(),
            "cache": get_cache_stats(),
            "system": {
                "environment": settings.sentry_environment,
                "demo_mode": settings.demo_mode,
                "redis_enabled": settings.redis_enabled,
            }
        }
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn

    logger.info(
        "Starting uvicorn server",
        extra={
            "host": settings.api_host,
            "port": settings.api_port,
            "workers": settings.worker_count,
        }
    )

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        workers=1 if settings.api_reload else settings.worker_count,
        log_level=settings.log_level.lower(),
    )
