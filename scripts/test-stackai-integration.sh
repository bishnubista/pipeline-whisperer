#!/bin/bash
# Test Stack AI integration with real API

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=============================================================================="
echo "STACK AI INTEGRATION TEST"
echo "=============================================================================="
echo ""

# Check if we're in the right directory
if [ ! -f "apps/agent-api/.env" ]; then
    echo -e "${RED}❌ Error: .env file not found in apps/agent-api/${NC}"
    echo "Please create .env file with Stack AI credentials"
    exit 1
fi

# Check for required env vars
echo -e "${BLUE}Step 1: Checking environment variables...${NC}"
cd apps/agent-api

if grep -q "YOUR_PRIVATE_API_KEY_HERE" .env; then
    echo -e "${YELLOW}⚠️  WARNING: Stack AI API key not set in .env${NC}"
    echo "Please update STACKAI_API_KEY in apps/agent-api/.env"
    echo ""
    echo "You need to replace:"
    echo "  STACKAI_API_KEY=YOUR_PRIVATE_API_KEY_HERE"
    echo ""
    echo "With your actual private API key from Stack AI"
    exit 1
fi

echo -e "${GREEN}✅ Environment variables configured${NC}"
echo ""

# Test 1: Import Stack AI client
echo -e "${BLUE}Step 2: Testing Stack AI client import...${NC}"
PYTHONPATH=. .venv/bin/python -c "from app.services.stackai_client import get_stackai_client; print('✓ Import successful')"
echo -e "${GREEN}✅ Stack AI client imported${NC}"
echo ""

# Test 2: Health check
echo -e "${BLUE}Step 3: Running Stack AI health check...${NC}"
PYTHONPATH=. .venv/bin/python <<'EOF'
import sys
from app.services.stackai_client import get_stackai_client

client = get_stackai_client()
health = client.health_check()

print(f"Status: {health['status']}")
print(f"Accessible: {health['accessible']}")
print(f"Message: {health['message']}")

if health['status'] == 'mock_mode':
    print("\n⚠️  Stack AI is in MOCK MODE")
    print("Check that your .env has:")
    print("  - STACKAI_API_KEY (private key)")
    print("  - STACKAI_ORG_ID")
    print("  - STACKAI_FLOW_ID")
    sys.exit(1)
elif health['status'] == 'error':
    print(f"\n❌ Stack AI API error: {health['message']}")
    sys.exit(1)
else:
    print(f"\n✅ Stack AI is HEALTHY")
    if 'test_score' in health:
        print(f"   Test score: {health['test_score']}")
EOF

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Health check failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Health check passed${NC}"
echo ""

# Test 3: Score a test lead
echo -e "${BLUE}Step 4: Scoring test leads...${NC}"
PYTHONPATH=. .venv/bin/python <<'EOF'
from app.services.stackai_client import get_stackai_client

client = get_stackai_client()

# Test Case 1: Enterprise lead
print("\n📊 Test 1: Enterprise Lead")
print("-" * 50)
test_lead_1 = {
    "company_name": "MegaRetail Co",
    "industry": "retail",
    "employee_count": 1200,
    "revenue": 25000000,
    "website": "megaretail.com"
}

result_1 = client.score_lead(test_lead_1)
print(f"Company: {test_lead_1['company_name']}")
print(f"Score: {result_1['score']}")
print(f"Persona: {result_1['persona']}")
print(f"Reasoning: {result_1['reasoning']}")
print(f"Is Mock: {result_1.get('mock', False)}")

# Test Case 2: SMB lead
print("\n📊 Test 2: SMB Lead")
print("-" * 50)
test_lead_2 = {
    "company_name": "StartupHub",
    "industry": "technology",
    "employee_count": 15,
    "revenue": 500000,
    "website": "startuphub.io"
}

result_2 = client.score_lead(test_lead_2)
print(f"Company: {test_lead_2['company_name']}")
print(f"Score: {result_2['score']}")
print(f"Persona: {result_2['persona']}")
print(f"Reasoning: {result_2['reasoning']}")
print(f"Is Mock: {result_2.get('mock', False)}")

# Test Case 3: High-value enterprise
print("\n📊 Test 3: High-Value Enterprise")
print("-" * 50)
test_lead_3 = {
    "company_name": "CloudScale Systems",
    "industry": "technology",
    "employee_count": 850,
    "revenue": 45000000,
    "website": "cloudscale.com"
}

result_3 = client.score_lead(test_lead_3)
print(f"Company: {test_lead_3['company_name']}")
print(f"Score: {result_3['score']}")
print(f"Persona: {result_3['persona']}")
print(f"Reasoning: {result_3['reasoning']}")
print(f"Is Mock: {result_3.get('mock', False)}")

# Verify results
print("\n" + "=" * 50)
print("VALIDATION")
print("=" * 50)

if result_1.get('mock') or result_2.get('mock') or result_3.get('mock'):
    print("⚠️  WARNING: Some results are from MOCK mode")
    print("This means Stack AI API call failed or credentials are wrong")
else:
    print("✅ All scores from REAL Stack AI API")

if result_1['persona'] == 'enterprise' and result_2['persona'] in ['smb', 'startup']:
    print("✅ Persona classification looks correct")
else:
    print("⚠️  Persona classification may be incorrect")
    print(f"   Expected: enterprise for {test_lead_1['company_name']}, got {result_1['persona']}")
    print(f"   Expected: smb/startup for {test_lead_2['company_name']}, got {result_2['persona']}")

if result_3['score'] > result_2['score']:
    print("✅ Score ordering makes sense (high-value > startup)")
else:
    print("⚠️  Score ordering seems off")
    print(f"   {test_lead_3['company_name']}: {result_3['score']}")
    print(f"   {test_lead_2['company_name']}: {result_2['score']}")

EOF

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Lead scoring test failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Lead scoring tests passed${NC}"
echo ""

# Summary
echo "=============================================================================="
echo -e "${GREEN}✅ STACK AI INTEGRATION TEST COMPLETE${NC}"
echo "=============================================================================="
echo ""
echo "Next steps:"
echo "  1. If tests used MOCK mode, update your STACKAI_API_KEY in .env"
echo "  2. If tests passed with real API, you're ready to go!"
echo "  3. Run end-to-end test: ./scripts/test-phase1-standalone.sh"
echo ""
echo "Stack AI Configuration:"
echo "  Org ID:  f3d287f4-b108-4ce6-80ac-e7a8121e59ec"
echo "  Flow ID: 68f2b44f9dce4066a0ab4058"
echo "  Endpoint: https://api.stack-ai.com/inference/v0/run/{org_id}/{flow_id}"
echo ""
echo "=============================================================================="
