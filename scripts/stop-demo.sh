#!/bin/bash
# Stop all demo services

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Stopping Pipeline Whisperer services..."

# Kill API server
if [ -f /tmp/pipeline-api.pid ]; then
    API_PID=$(cat /tmp/pipeline-api.pid)
    if kill $API_PID 2>/dev/null; then
        echo -e "${GREEN}✅ Stopped API server (PID: $API_PID)${NC}"
    else
        echo -e "${YELLOW}⚠️  API server not running${NC}"
    fi
    rm /tmp/pipeline-api.pid
fi

# Kill Next.js server
if [ -f /tmp/pipeline-web.pid ]; then
    WEB_PID=$(cat /tmp/pipeline-web.pid)
    if kill $WEB_PID 2>/dev/null; then
        echo -e "${GREEN}✅ Stopped dashboard (PID: $WEB_PID)${NC}"
    else
        echo -e "${YELLOW}⚠️  Dashboard not running${NC}"
    fi
    rm /tmp/pipeline-web.pid
fi

# Cleanup any remaining processes on ports
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    kill $(lsof -t -i:8000) 2>/dev/null
    echo -e "${GREEN}✅ Cleaned up port 8000${NC}"
fi

if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    kill $(lsof -t -i:3000) 2>/dev/null
    echo -e "${GREEN}✅ Cleaned up port 3000${NC}"
fi

echo ""
echo "All services stopped."
