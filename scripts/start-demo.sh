#!/bin/bash
# Quick-start script for hackathon demo

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=============================================================================="
echo "PIPELINE WHISPERER - QUICK START"
echo "=============================================================================="
echo ""

# Step 1: Populate data
echo -e "${BLUE}Step 1: Populating demo data...${NC}"
./scripts/demo.sh > /dev/null 2>&1
echo -e "${GREEN}✅ Data populated${NC}"
echo ""

# Step 2: Check if ports are available
echo -e "${BLUE}Step 2: Checking ports...${NC}"
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠️  Port 8000 in use, killing existing process${NC}"
    kill $(lsof -t -i:8000) 2>/dev/null || true
    sleep 2
fi

if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠️  Port 3000 in use, killing existing process${NC}"
    kill $(lsof -t -i:3000) 2>/dev/null || true
    sleep 2
fi
echo -e "${GREEN}✅ Ports available${NC}"
echo ""

# Step 3: Start API server
echo -e "${BLUE}Step 3: Starting API server...${NC}"
cd apps/agent-api
PYTHONPATH=. .venv/bin/python main.py > /tmp/pipeline-api.log 2>&1 &
API_PID=$!
cd ../..

# Wait for API to start
sleep 3
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo -e "${GREEN}✅ API running at http://localhost:8000 (PID: $API_PID)${NC}"
else
    echo -e "${RED}❌ API failed to start. Check /tmp/pipeline-api.log${NC}"
    exit 1
fi
echo ""

# Step 4: Start Next.js dashboard
echo -e "${BLUE}Step 4: Starting dashboard...${NC}"
cd apps/web
pnpm dev > /tmp/pipeline-web.log 2>&1 &
WEB_PID=$!
cd ../..

# Wait for Next.js to start
echo -e "${YELLOW}⏳ Waiting for Next.js to start (this may take 10-15 seconds)...${NC}"
sleep 15

if curl -s http://localhost:3000 >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Dashboard running at http://localhost:3000 (PID: $WEB_PID)${NC}"
else
    echo -e "${YELLOW}⚠️  Dashboard may still be starting. Check http://localhost:3000${NC}"
fi
echo ""

# Step 5: Save PIDs
echo "$API_PID" > /tmp/pipeline-api.pid
echo "$WEB_PID" > /tmp/pipeline-web.pid

# Instructions
echo "=============================================================================="
echo -e "${GREEN}✅ PIPELINE WHISPERER IS RUNNING!${NC}"
echo "=============================================================================="
echo ""
echo "🌐 Open your browser and navigate to:"
echo -e "   ${BLUE}http://localhost:3000${NC}"
echo ""
echo "📊 You should see:"
echo "   - Overview cards showing 16 leads, 5 conversions"
echo "   - Pipeline funnel visualization"
echo "   - 3 A/B experiments with Thompson Sampling parameters"
echo "   - Activity feed with recent events"
echo ""
echo "🎛️  Try the controls:"
echo "   - Click 'Pause' on any experiment"
echo "   - Watch the status change"
echo "   - Click 'Activate' to re-enable"
echo ""
echo "📝 Logs:"
echo "   API:       tail -f /tmp/pipeline-api.log"
echo "   Dashboard: tail -f /tmp/pipeline-web.log"
echo ""
echo "🛑 To stop all services:"
echo "   ./scripts/stop-demo.sh"
echo ""
echo "=============================================================================="
