#!/bin/bash
# Demo script for Pipeline Whisperer hackathon presentation
# Runs complete pipeline flow with visual feedback

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo "=============================================================================="
echo "PIPELINE WHISPERER - AUTONOMOUS GTM AGENT DEMO"
echo "=============================================================================="
echo ""
echo -e "${CYAN}This demo showcases the complete autonomous pipeline:${NC}"
echo "  1. Lead ingestion from Lightfield"
echo "  2. AI-powered scoring with stackAI"
echo "  3. Thompson Sampling experiment selection"
echo "  4. Personalized outreach via Truefoundry + Lightfield"
echo "  5. Autonomous learning from conversions"
echo ""
echo -e "${YELLOW}⚠️  Note: Using simulation mode (no real API calls required)${NC}"
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

if [ ! -f "apps/agent-api/pipeline.db" ]; then
    echo -e "${RED}❌ Database not found${NC}"
    echo "Run: cd apps/agent-api && uv run alembic upgrade head"
    exit 1
fi

if [ ! -f "apps/agent-api/.venv/bin/python" ]; then
    echo -e "${RED}❌ Virtual environment not found${NC}"
    echo "Run: cd apps/agent-api && uv venv && uv pip install -e ."
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites met${NC}"
echo ""

# Seed experiments if needed
EXPERIMENT_COUNT=$(sqlite3 apps/agent-api/pipeline.db "SELECT COUNT(*) FROM experiments;" 2>/dev/null || echo "0")

if [ "$EXPERIMENT_COUNT" -eq "0" ]; then
    echo "🌱 Seeding demo experiments..."
    PYTHONPATH=apps/agent-api apps/agent-api/.venv/bin/python scripts/seed_experiments.py
    echo ""
fi

# Phase 1: Lead Ingestion
echo "=== PHASE 1: LEAD INGESTION & SCORING ==="
echo ""
echo -e "${BLUE}📥 Simulating 5 new leads from Lightfield...${NC}"

PYTHONPATH=apps/agent-api apps/agent-api/.venv/bin/python <<EOF
import sys
sys.path.insert(0, 'apps/agent-api')

from app.models.base import SessionLocal
from app.models.lead import Lead, LeadStatus
from datetime import datetime, timezone
import random

db = SessionLocal()

companies = [
    ("TechCorp Inc", "technology", "enterprise"),
    ("FinanceFlow LLC", "finance", "enterprise"),
    ("StartupHub", "saas", "smb"),
    ("MegaRetail Co", "retail", "enterprise"),
    ("CloudScale Systems", "technology", "smb"),
]

for idx, (company, industry, persona) in enumerate(companies, 1):
    lead = Lead(
        lightfield_id=f"lf_demo_{int(datetime.now().timestamp())}_{idx}",
        company_name=company,
        contact_name=f"Contact {idx}",
        contact_email=f"contact{idx}@{company.lower().replace(' ', '')}.com",
        industry=industry,
        persona=persona.upper(),
        score=random.uniform(0.6, 0.95),  # High-scoring leads
        status=LeadStatus.SCORED,
        scored_at=datetime.now(timezone.utc),
    )
    db.add(lead)
    print(f"  ✓ {company} (score={lead.score:.2f}, persona={persona})")

db.commit()
db.close()
EOF

echo -e "${GREEN}✅ 5 leads ingested and scored${NC}"
echo ""
sleep 2

# Phase 2: Outreach Orchestration
echo "=== PHASE 2: OUTREACH ORCHESTRATION ==="
echo ""
echo -e "${PURPLE}🎯 Running Thompson Sampling to select experiments...${NC}"

PYTHONPATH=apps/agent-api apps/agent-api/.venv/bin/python <<EOF
import sys
sys.path.insert(0, 'apps/agent-api')

from app.models.base import SessionLocal
from app.models.lead import Lead, LeadStatus
from app.models.outreach_log import OutreachLog, OutreachStatus
from datetime import datetime, timezone
from services.workers.outreach_orchestrator_worker import select_experiment, process_scored_lead

db = SessionLocal()

# Get uncontacted scored leads
leads = db.query(Lead).filter(
    Lead.status == LeadStatus.SCORED,
    Lead.score >= 0.5
).limit(5).all()

print(f"\n📊 Processing {len(leads)} scored leads...\n")

for lead in leads:
    # Select experiment via Thompson Sampling
    exp = select_experiment(db, lead)
    if not exp:
        print(f"  ⚠️  No experiment available for {lead.company_name}")
        continue

    # Create mock outreach
    lead.experiment_id = exp.experiment_id
    lead.status = LeadStatus.CONTACTED
    lead.contacted_at = datetime.now(timezone.utc)
    lead.outreach_count = 1

    # Update experiment metrics
    exp.leads_assigned = (exp.leads_assigned or 0) + 1
    exp.outreach_sent = (exp.outreach_sent or 0) + 1
    exp.update_metrics()

    # Create outreach log
    outreach = OutreachLog(
        lead_id=lead.id,
        experiment_id=exp.experiment_id,
        template_id=f"tpl_{exp.experiment_id.split('_')[1]}",
        subject=f"Demo outreach to {lead.company_name}",
        body="Personalized message body...",
        channel="email",
        status=OutreachStatus.SENT,
        sent_at=datetime.now(timezone.utc),
    )
    db.add(outreach)

    print(f"  ✓ {lead.company_name}: Experiment={exp.experiment_id} (α={exp.alpha:.1f}, β={exp.beta:.1f})")

db.commit()
db.close()
EOF

echo ""
echo -e "${GREEN}✅ Outreach sent to all qualified leads${NC}"
echo ""
sleep 2

# Phase 3: Conversions & Learning
echo "=== PHASE 3: FEEDBACK LOOP & AUTONOMOUS LEARNING ==="
echo ""
echo -e "${CYAN}🎉 Simulating 2 conversions to trigger learning...${NC}"

PYTHONPATH=apps/agent-api apps/agent-api/.venv/bin/python <<EOF
import sys
sys.path.insert(0, 'apps/agent-api')

from app.models.base import SessionLocal
from app.models.lead import Lead, LeadStatus
from services.workers.feedback_loop_worker import process_engagement_event
from datetime import datetime, timezone

db = SessionLocal()

# Get 2 contacted leads to convert
leads = db.query(Lead).filter(
    Lead.status == LeadStatus.CONTACTED
).limit(2).all()

print("")
for lead in leads:
    event = {
        "event_type": "outreach.converted",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "lead_id": lead.id,
        "lightfield_id": lead.lightfield_id,
        "experiment_id": lead.experiment_id,
        "conversion_value": 1500.0,
    }

    success = process_engagement_event(event, db)

    if success:
        print(f"  ✓ {lead.company_name} CONVERTED! (experiment={lead.experiment_id})")
    else:
        print(f"  ✗ Failed to process conversion for {lead.company_name}")

db.close()
EOF

echo ""
echo -e "${GREEN}✅ Thompson Sampling priors updated${NC}"
echo ""
sleep 2

# Show results
echo "=== DEMO RESULTS ==="
echo ""
echo -e "${YELLOW}📈 Experiment Performance:${NC}"
echo ""

sqlite3 apps/agent-api/pipeline.db <<EOF
.mode column
.headers on
SELECT
    experiment_id,
    printf('%.1f', alpha) as alpha,
    printf('%.1f', beta) as beta,
    leads_assigned,
    outreach_sent,
    conversions,
    printf('%.1f%%', conversion_rate * 100) as cvr
FROM experiments
WHERE is_active = 1
ORDER BY conversions DESC;
EOF

echo ""
echo -e "${YELLOW}📊 Pipeline Metrics:${NC}"
echo ""

TOTAL_LEADS=$(sqlite3 apps/agent-api/pipeline.db "SELECT COUNT(*) FROM leads;")
SCORED_LEADS=$(sqlite3 apps/agent-api/pipeline.db "SELECT COUNT(*) FROM leads WHERE score IS NOT NULL;")
CONTACTED_LEADS=$(sqlite3 apps/agent-api/pipeline.db "SELECT COUNT(*) FROM leads WHERE status = 'CONTACTED';")
CONVERTED_LEADS=$(sqlite3 apps/agent-api/pipeline.db "SELECT COUNT(*) FROM leads WHERE status = 'CONVERTED';")

echo "  Total Leads:      $TOTAL_LEADS"
echo "  Scored Leads:     $SCORED_LEADS"
echo "  Contacted Leads:  $CONTACTED_LEADS"
echo "  Converted Leads:  $CONVERTED_LEADS"

if [ "$CONTACTED_LEADS" -gt "0" ]; then
    CONVERSION_RATE=$(echo "scale=1; $CONVERTED_LEADS * 100.0 / $CONTACTED_LEADS" | bc)
    echo "  Conversion Rate:  ${CONVERSION_RATE}%"
fi

echo ""
echo "=============================================================================="
echo -e "${GREEN}✅ DEMO COMPLETE!${NC}"
echo "=============================================================================="
echo ""
echo "Next Steps:"
echo "  1. View dashboard: cd apps/web && pnpm dev"
echo "  2. Open browser: http://localhost:3000"
echo "  3. See real-time metrics and experiment controls"
echo ""
echo -e "${CYAN}🎯 Key Insight:${NC} Experiments with higher conversion rates now get selected"
echo "   MORE often by Thompson Sampling - the system learns automatically!"
echo ""
