# Phase 1 - Complete Test Plan

## ✅ Environment Check - PASSED

Ran `python scripts/check_env.py` - Results:

```
✅ Database: SQLite (exists at apps/agent-api/pipeline.db)
✅ Kafka Brokers: localhost:19092
✅ Topics: leads.raw, leads.scored, outreach.events
✅ API: 0.0.0.0:8000
✅ stackAI: API key configured
⚠️  Sentry: Not configured (monitoring disabled)
ℹ️  Lightfield: Using simulator
ℹ️  Truefoundry: Phase 2
```

**Status**: Ready for testing (with Sentry warning - non-blocking)

---

## Test Execution Steps

### Step 1: Start Docker Infrastructure

```bash
# Start Docker Desktop first!
./scripts/start-infra.sh
```

**Expected Output:**
```
✅ Redpanda is healthy
✅ PostgreSQL is ready
Topics created: leads.raw, leads.scored, outreach.events
```

**Verify:**
- Redpanda Console: http://localhost:8080
- Docker containers running: `docker ps`

---

### Step 2: Start FastAPI Server

**Terminal 1:**
```bash
cd apps/agent-api
uv run python main.py
```

**Expected Output:**
```
🚀 Pipeline Whisperer Agent API starting...
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Verify:**
```bash
curl http://localhost:8000/health | jq
curl http://localhost:8000/metrics | jq
```

Should return healthy status and zero metrics.

---

### Step 3: Start Lead Scorer Worker

**Terminal 2:**
```bash
uv run --directory apps/agent-api python services/workers/lead_scorer_worker.py
```

**Expected Output:**
```
LEAD SCORER WORKER
Lead scorer worker initialized
Subscribed to: leads.raw
Starting lead scorer worker...
```

**Verify:**
- No errors
- Consumer connected to Kafka

---

### Step 4: Ingest Demo Leads

**Terminal 3:**
```bash
uv run --directory apps/agent-api python scripts/ingest_demo_leads.py
```

**Input:**
- How many leads? `5`
- Delay? `1.0`

**Expected Output:**
```
[1/5] Publishing: Rodriguez, Figueroa and Sanchez - Amanda Davis
  ✅ Published to Kafka
[2/5] Publishing: Cole LLC - Christopher Bernard
  ✅ Published to Kafka
...
✅ Published: 5
```

**Verify in Terminal 2 (Worker):**
Should see:
```
Processing lead: lf_ad3c2d6d-...
Scored lead lf_ad3c2d6d-...: 0.612
Persisted lead lf_ad3c2d6d-... to database (ID: 1)
```

---

## Verification Tests

### Test 1: Database Check

```bash
cd apps/agent-api
sqlite3 pipeline.db "SELECT COUNT(*) FROM leads;"
```

**Expected**: `5` (or number of leads ingested)

```bash
sqlite3 pipeline.db "SELECT id, company_name, score, persona, status FROM leads LIMIT 3;"
```

**Expected**: 3 rows with scored leads

---

### Test 2: API Endpoints

**List all leads:**
```bash
curl http://localhost:8000/leads/ | jq
```

**Expected**: Array of 5 leads with full details

**Get statistics:**
```bash
curl http://localhost:8000/leads/stats | jq
```

**Expected**:
```json
{
  "total_leads": 5,
  "by_status": {"scored": 5},
  "by_persona": {"enterprise": 2, "smb": 2, "individual": 1},
  "avg_score": 0.687,
  "top_industries": [...]
}
```

**Filter by persona:**
```bash
curl "http://localhost:8000/leads/?persona=enterprise" | jq
```

**Expected**: Only enterprise leads

**Get single lead:**
```bash
curl http://localhost:8000/leads/1 | jq
```

**Expected**: Full lead details with scoring_metadata

---

### Test 3: Kafka Topics

Open Redpanda Console: http://localhost:8080

**Verify:**
1. Topic `leads.raw` has 5 messages
2. Topic `leads.scored` has 5 messages
3. Consumer group `lead-scorer-group` shows commits

---

### Test 4: Interactive API Docs

Open: http://localhost:8000/docs

**Try:**
1. GET /leads - Execute and see results
2. GET /leads/stats - View aggregates
3. GET /health - Verify health
4. GET /metrics - See real-time counts

---

## Success Criteria

- [ ] Infrastructure starts without errors
- [ ] API server responds to health checks
- [ ] Worker connects to Kafka
- [ ] Leads are generated and published
- [ ] Worker consumes and scores leads
- [ ] Leads appear in database with scores
- [ ] API endpoints return correct data
- [ ] Kafka topics contain messages
- [ ] No crashes or exceptions

---

## Known Issues & Workarounds

### Issue: Docker not running
**Solution**: Start Docker Desktop before `./scripts/start-infra.sh`

### Issue: Port 8000 already in use
**Solution**:
```bash
lsof -ti:8000 | xargs kill -9
```

### Issue: Database locked
**Solution**: Only one writer at a time for SQLite. This is expected. For concurrent writes, switch to PostgreSQL.

### Issue: Kafka connection refused
**Solution**: Ensure Redpanda is running:
```bash
docker ps | grep redpanda
```

---

## Performance Benchmarks

**Expected Performance:**
- Lead generation: ~100 leads/sec
- Kafka publish: ~500 msg/sec
- End-to-end (generate→kafka→score→db): ~50 leads/sec
- API response time: <50ms

**Test with 100 leads:**
```bash
# In ingestion script, enter: 100 leads, 0.1s delay
# Should complete in ~10-15 seconds
```

---

## Cleanup

```bash
# Stop all services
docker compose -f docker/docker-compose.yaml down

# Remove data (optional)
docker compose -f docker/docker-compose.yaml down -v
rm apps/agent-api/pipeline.db
```

---

## Next Steps After Successful Test

1. ✅ Commit environment fixes
2. ✅ Update testing documentation
3. ✅ Create PR for Phase 1
4. 🚀 Begin Phase 2 (Truefoundry + Outreach)

---

**Test Date**: 2025-10-17
**Tester**: (your name)
**Status**: Awaiting Docker startup
**Repository**: https://github.com/bishnubista/pipeline-whisperer
**Branch**: feat/phase1-lead-ingestion
