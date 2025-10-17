"""
Pipeline Whisperer Agent API
Main FastAPI application with Sentry instrumentation
"""
import os
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize Sentry
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN_PYTHON"),
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
    environment=os.getenv("SENTRY_ENVIRONMENT", "development"),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print("🚀 Pipeline Whisperer Agent API starting...")

    # TODO: Initialize Kafka consumers
    # TODO: Initialize database connections

    yield

    # Shutdown
    print("👋 Pipeline Whisperer Agent API shutting down...")
    # TODO: Cleanup resources


app = FastAPI(
    title="Pipeline Whisperer Agent API",
    description="Autonomous GTM agent powered by Lightfield, stackAI, Redpanda, Truefoundry, and Sentry",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Pipeline Whisperer Agent API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    """Health check endpoint for Docker and monitoring"""
    return {
        "status": "healthy",
        "components": {
            "api": "operational",
            # TODO: Add Kafka, DB, Sentry checks
        }
    }


@app.get("/metrics")
async def metrics():
    """Basic metrics endpoint"""
    return {
        "leads_processed": 0,
        "outreach_sent": 0,
        "conversions": 0,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("API_RELOAD", "true").lower() == "true",
    )
