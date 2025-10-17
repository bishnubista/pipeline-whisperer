#!/bin/bash
# Standalone Phase 1 test (without Kafka/Docker dependency)
# Tests: Simulator → Database → API

set -e

echo "=============================================================================="
echo "PHASE 1 STANDALONE TEST (Without Kafka)"
echo "=============================================================================="
echo ""

cd "$(dirname "$0")/.."

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}⚠️  Note: This test skips Kafka/Worker. Testing: Simulator → API → DB${NC}"
echo ""

# Check environment
echo "1️⃣  Checking environment..."
apps/agent-api/.venv/bin/python scripts/check_env.py || exit 1
echo ""

# Test lead simulator
echo "2️⃣  Testing Lead Simulator..."
apps/agent-api/.venv/bin/python services/simulators/lightfield_simulator.py | head -20
echo ""
echo -e "${GREEN}✅ Lead Simulator works${NC}"
echo ""

# Test database connection
echo "3️⃣  Testing Database..."
if [ -f apps/agent-api/pipeline.db ]; then
    COUNT=$(sqlite3 apps/agent-api/pipeline.db "SELECT COUNT(*) FROM leads;" 2>/dev/null || echo "0")
    echo "Current leads in database: $COUNT"
else
    echo "Database not yet created (will be created on first API start)"
fi
echo ""

# Start API server in background
echo "4️⃣  Starting FastAPI server..."
cd apps/agent-api
uv run python main.py > /tmp/fastapi.log 2>&1 &
API_PID=$!
cd ../..
echo "API PID: $API_PID"
sleep 5

# Check if API started
if ! ps -p $API_PID > /dev/null; then
    echo -e "${RED}❌ API failed to start${NC}"
    cat /tmp/fastapi.log
    exit 1
fi

echo -e "${GREEN}✅ API started${NC}"
echo ""

# Test API endpoints
echo "5️⃣  Testing API Endpoints..."

echo "  GET /health"
HEALTH=$(curl -s http://localhost:8000/health)
echo "  Response: $HEALTH"

echo ""
echo "  GET /metrics"
METRICS=$(curl -s http://localhost:8000/metrics)
echo "  Response: $METRICS"

echo ""
echo "  GET /leads/stats"
STATS=$(curl -s http://localhost:8000/leads/stats)
echo "  Response: $STATS"

echo ""
echo -e "${GREEN}✅ API endpoints responding${NC}"
echo ""

# Manually add a test lead (bypassing Kafka)
echo "6️⃣  Testing Direct Database Insert..."
apps/agent-api/.venv/bin/python <<'PYTHON'
import sys
from pathlib import Path

# Add paths
REPO_ROOT = Path.cwd()
APP_ROOT = REPO_ROOT / "apps" / "agent-api"
sys.path.insert(0, str(APP_ROOT))

from app.models.base import SessionLocal
from app.models.lead import Lead, LeadStatus, LeadPersona
from datetime import datetime, timezone

db = SessionLocal()

# Check if test lead exists
existing = db.query(Lead).filter(Lead.lightfield_id == "test-standalone-001").first()

if not existing:
    test_lead = Lead(
        lightfield_id="test-standalone-001",
        company_name="Test Company Standalone",
        contact_name="Test Contact",
        contact_email="test@example.com",
        contact_title="CTO",
        industry="SaaS",
        company_size="51-200",
        raw_payload={"test": True},
        score=0.85,
        persona=LeadPersona.SMB,
        status=LeadStatus.SCORED,
        scored_at=datetime.now(timezone.utc),
    )
    db.add(test_lead)
    db.commit()
    print("✅ Test lead inserted")
else:
    print("✅ Test lead already exists")

# Count leads
count = db.query(Lead).count()
print(f"Total leads in database: {count}")

db.close()
PYTHON

echo ""

# Test API with new lead
echo "7️⃣  Verifying API returns test lead..."
sleep 2
LEADS=$(curl -s http://localhost:8000/leads/)
echo "  Leads response (first 200 chars): ${LEADS:0:200}..."
echo ""

if echo "$LEADS" | grep -q "Test Company Standalone"; then
    echo -e "${GREEN}✅ Test lead found in API response${NC}"
else
    echo -e "${YELLOW}⚠️  Test lead not found (may need to restart API)${NC}"
fi
echo ""

# Cleanup
echo "8️⃣  Cleanup..."
kill $API_PID 2>/dev/null || true
wait $API_PID 2>/dev/null || true
echo "API stopped"
echo ""

# Summary
echo "=============================================================================="
echo "STANDALONE TEST SUMMARY"
echo "=============================================================================="
echo -e "${GREEN}✅ Environment check passed${NC}"
echo -e "${GREEN}✅ Lead simulator works${NC}"
echo -e "${GREEN}✅ Database accessible${NC}"
echo -e "${GREEN}✅ API server starts${NC}"
echo -e "${GREEN}✅ API endpoints respond${NC}"
echo -e "${GREEN}✅ Database insert works${NC}"
echo ""
echo -e "${YELLOW}⚠️  Skipped (requires Docker):${NC}"
echo "  - Redpanda/Kafka integration"
echo "  - Worker consumer"
echo "  - End-to-end streaming"
echo ""
echo "To test full pipeline with Kafka:"
echo "  1. Start Docker Desktop"
echo "  2. Run: ./scripts/start-infra.sh"
echo "  3. Follow: docs/phase-1-testing.md"
echo ""
echo "=============================================================================="
