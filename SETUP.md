# Pipeline Whisperer - Setup Guide

## Prerequisites

Before starting, ensure you have the following installed:

- **Node.js** 20.11.1 LTS or higher
- **Python** 3.11.8 or higher
- **Docker** and Docker Compose v2.24.5 or higher
- **pnpm** 9.1.1 (optional but recommended) or npm

## Quick Start

### 1. Clone and Setup Environment

```bash
# Run the automated setup script
./scripts/setup-dev.sh
```

This script will:
- Create a Python virtual environment
- Install Python dependencies
- Install Node.js dependencies
- Create `.env` from `.env.example`

### 2. Configure API Keys

Edit the `.env` file and add your credentials:

```bash
# Required for full functionality
LIGHTFIELD_API_KEY=your_lightfield_key
STACKAI_API_KEY=your_stackai_key
TRUEFOUNDRY_API_KEY=your_truefoundry_key
SENTRY_DSN_NEXTJS=your_sentry_dsn
SENTRY_DSN_PYTHON=your_sentry_dsn
```

**Note**: For initial testing, you can use demo mode without all credentials. Set:
```bash
DEMO_MODE=true
SIMULATE_LIGHTFIELD=true
```

### 3. Start Infrastructure Services

```bash
# Make sure Docker Desktop is running, then:
./scripts/start-infra.sh
```

This will start:
- **Redpanda** (Kafka-compatible streaming) on port 19092
- **PostgreSQL** database on port 5432
- **Redpanda Console** (UI) on port 8080

Access Redpanda Console at: http://localhost:8080

### 4. Start the FastAPI Backend

```bash
cd apps/agent-api
source venv/bin/activate  # On Windows: venv\Scripts\activate
python main.py
```

The API will be available at: http://localhost:8000
- Health check: http://localhost:8000/health
- API docs: http://localhost:8000/docs

### 5. Start the Next.js Frontend

```bash
cd apps/web
pnpm install  # or npm install
pnpm dev      # or npm run dev
```

The web UI will be available at: http://localhost:3000

## Project Structure

```
pipeline-whisperer-agent/
├── apps/
│   ├── web/              # Next.js frontend (TypeScript + Tailwind)
│   │   ├── app/          # App router pages
│   │   ├── sentry.*.config.ts  # Sentry instrumentation
│   │   └── package.json
│   └── agent-api/        # FastAPI backend (Python)
│       ├── app/
│       │   ├── config/   # Settings and configuration
│       │   ├── models/   # Database models (SQLAlchemy)
│       │   ├── routes/   # API endpoints
│       │   └── services/ # Business logic
│       ├── main.py       # FastAPI application entry
│       └── requirements.txt
├── services/
│   ├── workers/          # Kafka consumers and async workers
│   └── simulators/       # Demo data generators
├── docker/
│   └── docker-compose.yaml  # Infrastructure services
└── scripts/
    ├── setup-dev.sh      # Development setup automation
    └── start-infra.sh    # Infrastructure startup
```

## Verifying the Setup

### Check Infrastructure Health

```bash
# Check Docker services
docker compose -f docker/docker-compose.yaml ps

# List Kafka topics
docker exec pipeline-redpanda rpk topic list

# Expected topics:
# - leads.raw
# - leads.scored
# - outreach.events

# Check PostgreSQL
docker exec pipeline-postgres psql -U pipeline_user -d pipeline_db -c "\dt"
```

### Test API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Metrics
curl http://localhost:8000/metrics
```

### Check Sentry Integration

Once you've configured Sentry DSNs, trigger a test event:

```bash
# The API and web app will automatically send events
# Check your Sentry dashboard for incoming events
```

## Development Workflow

### Running Tests

```bash
# Python tests (to be added)
cd apps/agent-api
pytest

# Next.js tests (to be added)
cd apps/web
pnpm test
```

### Viewing Logs

```bash
# Infrastructure logs
docker compose -f docker/docker-compose.yaml logs -f

# Specific service
docker compose -f docker/docker-compose.yaml logs -f redpanda
```

### Stopping Services

```bash
# Stop infrastructure
docker compose -f docker/docker-compose.yaml down

# Stop and remove volumes (WARNING: deletes data)
docker compose -f docker/docker-compose.yaml down -v
```

## Troubleshooting

### Docker Issues

**Problem**: "Cannot connect to Docker daemon"
**Solution**: Start Docker Desktop

**Problem**: Port already in use
**Solution**: Stop conflicting services or change ports in `.env` and `docker-compose.yaml`

### Python Issues

**Problem**: Module not found
**Solution**: Ensure virtual environment is activated:
```bash
cd apps/agent-api
source venv/bin/activate
pip install -r requirements.txt
```

### Node.js Issues

**Problem**: Module not found or version conflicts
**Solution**: Clear cache and reinstall:
```bash
cd apps/web
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

## Next Steps

See `PLAN.md` for the phased implementation plan. Phase 0 (Foundations) is now complete!

**Current Status**: ✅ Phase 0 Complete
- Project structure created
- Infrastructure configured
- Health endpoints operational
- Ready for Phase 1: Lead Ingestion & Scoring

## Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Redpanda Documentation](https://docs.redpanda.com)
- [Sentry Documentation](https://docs.sentry.io)
