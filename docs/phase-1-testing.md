# Phase 1 - Lead Ingestion & Scoring - Testing Guide

## Overview

Phase 1 implements the complete lead ingestion pipeline:
1. **Lightfield simulator** generates realistic leads
2. **Kafka producer** publishes to `leads.raw` topic
3. **Worker consumes** from Kafka, scores with stackAI (mock), persists to DB
4. **API endpoints** expose lead data
5. **Sentry** tracks all operations

## Prerequisites

Ensure infrastructure is running:
```bash
# Start Redpanda + PostgreSQL
./scripts/start-infra.sh

# Verify services
docker ps  # Should see redpanda, postgres, redpanda-console
```

## End-to-End Test

### Terminal 1: Start API Server

```bash
cd apps/agent-api
uv run python main.py
```

Expected output:
```
🚀 Pipeline Whisperer Agent API starting...
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Terminal 2: Start Lead Scorer Worker

```bash
cd /Users/bishnubista/Projects/hackathon/pipeline-whisperer-agent
PYTHONPATH=apps/agent-api apps/agent-api/.venv/bin/python services/workers/lead_scorer_worker.py
```

Expected output:
```
================================================================================
LEAD SCORER WORKER
================================================================================
INFO - Lead scorer worker initialized
INFO - Subscribed to: leads.raw
INFO - Starting lead scorer worker...
```

### Terminal 3: Ingest Demo Leads

```bash
cd /Users/bishnubista/Projects/hackathon/pipeline-whisperer-agent
PYTHONPATH=apps/agent-api apps/agent-api/.venv/bin/python scripts/ingest_demo_leads.py
```

Interactive prompts:
- **How many leads?** Enter `5` (start small)
- **Delay?** Enter `2.0` (2 seconds between leads)

Expected flow:
1. Script generates leads using Faker
2. Publishes to Kafka `leads.raw` topic
3. Worker consumes, scores, persists
4. Worker publishes to `leads.scored` topic

### Verify Results

**Check Database:**
```bash
cd apps/agent-api
sqlite3 pipeline.db "SELECT id, company_name, score, persona, status FROM leads;"
```

Expected output:
```
1|Rodriguez, Figueroa and Sanchez|0.612|individual|scored
2|Cole LLC|0.785|enterprise|scored
3|Blair PLC|0.691|smb|scored
...
```

**Check API:**
```bash
# List all leads
curl http://localhost:8000/leads/ | jq

# Get statistics
curl http://localhost:8000/leads/stats | jq

# Filter by persona
curl "http://localhost:8000/leads/?persona=enterprise" | jq

# Get metrics
curl http://localhost:8000/metrics | jq
```

**Check Redpanda Console:**
Open http://localhost:8080 and verify:
- Topic `leads.raw` has messages
- Topic `leads.scored` has messages
- Consumer group `lead-scorer-group` is active

## Component Testing

### 1. Test Lead Simulator

```bash
PYTHONPATH=apps/agent-api apps/agent-api/.venv/bin/python services/simulators/lightfield_simulator.py
```

Should generate 3 sample leads with realistic data.

### 2. Test Kafka Producer

```python
# In Python REPL
import sys
sys.path.insert(0, 'apps/agent-api')
from app.services.kafka_producer import get_kafka_producer

producer = get_kafka_producer()
test_lead = {
    "lightfield_id": "test-123",
    "company": {"name": "Test Co"},
    "contact": {"name": "John Doe"}
}
producer.publish_lead(test_lead)
producer.flush()
```

### 3. Test API Endpoints

```bash
# Interactive API docs
open http://localhost:8000/docs

# Health check
curl http://localhost:8000/health

# Root
curl http://localhost:8000/
```

## Troubleshooting

### Worker not consuming messages

**Problem:** Worker starts but doesn't process leads

**Solutions:**
1. Check Kafka is running: `docker ps | grep redpanda`
2. Verify topic exists: `docker exec pipeline-redpanda rpk topic list`
3. Check consumer group: `docker exec pipeline-redpanda rpk group list`

### Database locked error

**Problem:** `database is locked`

**Solution:** Only one process can write to SQLite at a time. This is expected in demo mode. For production, use PostgreSQL from docker-compose.

### Import errors

**Problem:** `ModuleNotFoundError: No module named 'app'`

**Solution:** Set PYTHONPATH:
```bash
export PYTHONPATH=/Users/bishnubista/Projects/hackathon/pipeline-whisperer-agent/apps/agent-api
```

### Kafka connection refused

**Problem:** `Connection refused` to localhost:19092

**Solution:**
```bash
# Restart infrastructure
docker compose -f docker/docker-compose.yaml down
./scripts/start-infra.sh
```

## Performance Metrics

Expected performance (local MacBook):
- **Lead generation:** ~100 leads/second
- **Kafka publish:** ~500 messages/second
- **Scoring + DB persist:** ~50 leads/second (with mock stackAI)
- **API response time:** <50ms for list, <10ms for single lead

## Next Steps

- [ ] Switch to PostgreSQL for concurrent writes
- [ ] Implement real stackAI API integration
- [ ] Add Truefoundry outreach orchestration (Phase 2)
- [ ] Build Next.js dashboard
- [ ] Add authentication & rate limiting

## Demo Script for Presentation

```bash
# Terminal 1: API
cd apps/agent-api && uv run python main.py

# Terminal 2: Worker (wait 5s)
PYTHONPATH=apps/agent-api apps/agent-api/.venv/bin/python services/workers/lead_scorer_worker.py

# Terminal 3: Ingest (wait 5s)
PYTHONPATH=apps/agent-api apps/agent-api/.venv/bin/python scripts/ingest_demo_leads.py
# Enter: 10 leads, 1.0s delay

# Terminal 4: Watch results
watch -n 1 'curl -s http://localhost:8000/metrics | jq'

# Show dashboard
open http://localhost:8000/docs
```

---

**Status:** Phase 1 - 90% Complete
**Last Updated:** 2025-10-17
**Repository:** https://github.com/bishnubista/pipeline-whisperer
