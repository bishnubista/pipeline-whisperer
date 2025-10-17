# Real API Integration Plan

**Branch:** `feat/real-api-integration`
**Goal:** Replace mock implementations with real API calls to Lightfield, Truefoundry, and stackAI

---

## Current Architecture (Mock Mode)

### Overview
All three external services currently operate in **mock mode** for demo reliability:

1. **stackAI** - Lead scoring (services/workers/lead_scorer_worker.py)
2. **Truefoundry** - AI-powered personalization (apps/agent-api/app/services/truefoundry_client.py)
3. **Lightfield** - Multi-channel outreach (apps/agent-api/app/services/lightfield_client.py)

### Mock Trigger Conditions
```python
# Mock mode activates when:
1. API key is None or starts with "your_"
2. settings.demo_mode = True (for stackAI)
3. settings.simulate_lightfield = True (for Lightfield)
```

---

## Integration Checklist

### Phase 1: stackAI Integration (Lead Scoring)

**File:** `services/workers/lead_scorer_worker.py:72-95`

**Current Mock Behavior:**
```python
def _mock_stackai_scoring(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
    # Random score between 0.5-0.95
    score = random.uniform(0.5, 0.95)
    # Persona based on industry
    persona = "enterprise" if industry in enterprise_list else "smb"
```

**Real API Implementation Required:**

#### API Endpoint Research
- [ ] **Confirm stackAI endpoint**: What is the actual scoring endpoint?
  - Base URL: `https://api.stack-ai.com` or similar?
  - Endpoint path: `/v1/score`, `/predict`, or custom project endpoint?
- [ ] **Authentication method**: Bearer token? API key in header?
- [ ] **Request payload format**: What fields does stackAI expect?
  ```json
  {
    "company_name": "TechCorp Inc",
    "industry": "technology",
    "employee_count": 500,
    "revenue": 10000000,
    "website": "techcorp.com"
  }
  ```
- [ ] **Response format**: What does stackAI return?
  ```json
  {
    "score": 0.87,
    "confidence": 0.92,
    "persona": "enterprise",
    "reasoning": "High revenue, established company"
  }
  ```

#### Implementation Steps
1. [ ] Create `app/services/stackai_client.py` (similar pattern to other clients)
2. [ ] Add stackAI-specific error handling and retries
3. [ ] Update `lead_scorer_worker.py` to use real client
4. [ ] Add fallback to mock if API fails (graceful degradation)
5. [ ] Log API usage for monitoring

**Code Template:**
```python
class StackAIClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("STACKAI_API_KEY")
        self.project_id = os.getenv("STACKAI_PROJECT_ID")
        self.base_url = "https://api.stack-ai.com/v1"  # TBD

        if not self.api_key or self.api_key.startswith("your_"):
            self.mock_mode = True
        else:
            self.mock_mode = False

    def score_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.mock_mode:
            return self._mock_score(lead_data)

        try:
            response = httpx.post(
                f"{self.base_url}/projects/{self.project_id}/score",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=lead_data,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"stackAI API failed: {e}, falling back to mock")
            return self._mock_score(lead_data)
```

---

### Phase 2: Truefoundry Integration (AI Personalization)

**File:** `apps/agent-api/app/services/truefoundry_client.py:41-84`

**Current Mock Behavior:**
```python
def _mock_generate_message(self, template: str, lead_data: Dict[str, Any]):
    # Simple {{variable}} replacement
    body = template.replace("{{company_name}}", lead_data["company_name"])
    subject = f"{lead_data['company_name']} x Pipeline Whisperer"
```

**Real API Implementation Required:**

#### API Endpoint Research
- [ ] **Confirm Truefoundry endpoint**: What is the personalization endpoint?
  - Base URL: `https://api.truefoundry.com` (configured in settings.py)
  - Endpoint path: `/v1/agents/personalize` or custom deployment URL?
- [ ] **Workspace configuration**: How to specify workspace ID?
- [ ] **Request payload**: What fields does Truefoundry expect?
  ```json
  {
    "workspace": "ws_abc123",
    "template": "Hi {{contact_name}}, I noticed {{company_name}}...",
    "lead_data": {
      "company_name": "TechCorp",
      "contact_name": "John Doe",
      "industry": "SaaS"
    },
    "personalization_instructions": "Make it casual and friendly",
    "config": {
      "tone": "casual",
      "max_tokens": 500
    }
  }
  ```
- [ ] **Response format**: Subject + body or just body?
  ```json
  {
    "subject": "Quick question about TechCorp's growth",
    "body": "Hi John,\n\nI noticed TechCorp is scaling fast..."
  }
  ```

#### Implementation Steps
1. [ ] Verify Truefoundry authentication (Bearer token vs API key)
2. [ ] Test with minimal payload to validate endpoint
3. [ ] Add retry logic for rate limiting (429 responses)
4. [ ] Implement template caching if API has quota limits
5. [ ] Update `outreach_orchestrator_worker.py` to handle new response format

**Testing Strategy:**
```bash
# Test with curl first
curl -X POST https://api.truefoundry.com/v1/agents/personalize \
  -H "Authorization: Bearer $TRUEFOUNDRY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"workspace":"...","template":"...","lead_data":{...}}'
```

---

### Phase 3: Lightfield Integration (Multi-Channel Outreach)

**File:** `apps/agent-api/app/services/lightfield_client.py:46-104`

**Current Mock Behavior:**
```python
def _mock_send_email(self, to_email: str, to_name: str, subject: str):
    message_id = f"lf_msg_{uuid.uuid4().hex[:16]}"
    logger.info(f"📧 [SIMULATED] Email sent to {to_name}")
    return {"message_id": message_id, "status": "sent", "simulated": True}
```

**Real API Implementation Required:**

#### API Endpoint Research
- [ ] **Confirm Lightfield endpoint**: Email sending endpoint
  - Base URL: `https://api.lightfield.ai/v1` (configured in settings.py)
  - Endpoint: `/messages/email/send` (already implemented in code)
- [ ] **Authentication**: Bearer token or API key?
- [ ] **Request payload verification**:
  ```json
  {
    "to": {
      "email": "john@techcorp.com",
      "name": "John Doe"
    },
    "from": {
      "name": "Pipeline Whisperer"
    },
    "subject": "Quick question about TechCorp",
    "body": "Hi John...",
    "tracking_id": "lead_123",
    "timestamp": "2025-10-17T20:00:00Z"
  }
  ```
- [ ] **Response format**: Message ID for tracking?
  ```json
  {
    "message_id": "lf_msg_abc123xyz",
    "status": "queued",
    "scheduled_at": "2025-10-17T20:00:05Z"
  }
  ```
- [ ] **Webhook setup**: For engagement callbacks (opens, clicks, replies)

#### Implementation Steps
1. [ ] Remove `SIMULATE_LIGHTFIELD=true` environment variable
2. [ ] Verify Lightfield API key is valid
3. [ ] Test single email send with real API
4. [ ] Implement webhook endpoint for engagement tracking:
   - `POST /webhooks/lightfield/engagement`
   - Handle `opened_at`, `clicked_at`, `replied_at` events
5. [ ] Update `outreach_logs` table when webhooks fire
6. [ ] Connect webhooks to Phase 3 feedback loop

**Webhook Handler Template:**
```python
# apps/agent-api/app/routes/webhooks.py
@router.post("/webhooks/lightfield/engagement")
async def handle_lightfield_webhook(
    payload: Dict[str, Any],
    signature: str = Header(None, alias="X-Lightfield-Signature")
):
    # Verify webhook signature
    if not verify_lightfield_signature(payload, signature):
        raise HTTPException(401, "Invalid signature")

    # Update outreach_logs
    message_id = payload.get("message_id")
    event_type = payload.get("event")  # "opened", "clicked", "replied"

    if event_type == "opened":
        db.query(OutreachLog).filter_by(
            external_message_id=message_id
        ).update({"opened_at": datetime.now(timezone.utc)})

    # Publish to Kafka for Phase 3 feedback loop
    kafka_producer.produce("outreach.events", payload)
```

---

## Environment Configuration Updates

### New .env Variables Required

```bash
# === stackAI (Real API) ===
STACKAI_API_KEY=sk-stackai-abc123...
STACKAI_PROJECT_ID=proj_xyz789
STACKAI_BASE_URL=https://api.stack-ai.com/v1

# === Truefoundry (Real API) ===
TRUEFOUNDRY_API_KEY=tfy-abc123...
TRUEFOUNDRY_WORKSPACE=ws-pipeline-whisperer-prod
TRUEFOUNDRY_BASE_URL=https://api.truefoundry.com

# === Lightfield (Real API) ===
LIGHTFIELD_API_KEY=lf_live_abc123...
LIGHTFIELD_BASE_URL=https://api.lightfield.ai/v1
LIGHTFIELD_WEBHOOK_SECRET=whsec_abc123...
SIMULATE_LIGHTFIELD=false  # ⚠️ Change to false for real API

# === Feature Flags ===
DEMO_MODE=false  # ⚠️ Disable demo mode for real APIs
USE_REAL_APIS=true  # Optional explicit flag
```

### Update `settings.py`

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # stackAI (add base_url)
    stackai_api_key: str | None = None
    stackai_project_id: str | None = None
    stackai_base_url: str = "https://api.stack-ai.com/v1"  # NEW

    # Lightfield (add webhook secret)
    lightfield_api_key: str | None = None
    lightfield_base_url: str = "https://api.lightfield.ai/v1"
    lightfield_webhook_secret: str | None = None  # NEW

    # Feature flags
    demo_mode: bool = True
    simulate_lightfield: bool = True
    use_real_apis: bool = False  # NEW master switch
```

---

## Testing Strategy

### Unit Tests (Per Service)

```bash
# Test stackAI client
PYTHONPATH=apps/agent-api python -m pytest tests/test_stackai_client.py -v

# Test Truefoundry client
PYTHONPATH=apps/agent-api python -m pytest tests/test_truefoundry_client.py -v

# Test Lightfield client
PYTHONPATH=apps/agent-api python -m pytest tests/test_lightfield_client.py -v
```

### Integration Test (End-to-End)

```bash
# Full pipeline with real APIs
./scripts/test-real-apis.sh
```

**Test Script Content:**
```bash
#!/bin/bash
# Test real API integration end-to-end

set -e

echo "🧪 Testing Real API Integration"
echo "================================"

# 1. Verify env vars
echo "Step 1: Checking environment variables..."
if [ -z "$STACKAI_API_KEY" ]; then
  echo "❌ STACKAI_API_KEY not set"
  exit 1
fi
echo "✅ Environment configured"

# 2. Start API server with real APIs enabled
echo "Step 2: Starting API server (real APIs)..."
cd apps/agent-api
DEMO_MODE=false SIMULATE_LIGHTFIELD=false \
  PYTHONPATH=. .venv/bin/python main.py &
API_PID=$!
sleep 3

# 3. Publish test lead
echo "Step 3: Publishing test lead to Kafka..."
python scripts/test_lead_injection.py

# 4. Monitor lead_scorer_worker
echo "Step 4: Running lead scorer worker..."
PYTHONPATH=. .venv/bin/python services/workers/lead_scorer_worker.py &
WORKER_PID=$!
sleep 5

# 5. Check database for scored lead
echo "Step 5: Verifying lead scored..."
sqlite3 pipeline.db "SELECT company_name, score, persona FROM leads ORDER BY id DESC LIMIT 1;"

# 6. Run outreach orchestrator
echo "Step 6: Triggering outreach..."
PYTHONPATH=. .venv/bin/python services/workers/outreach_orchestrator_worker.py &
OUTREACH_PID=$!
sleep 5

# 7. Check outreach_logs
echo "Step 7: Verifying outreach sent..."
sqlite3 pipeline.db "SELECT status, external_message_id FROM outreach_logs ORDER BY id DESC LIMIT 1;"

# Cleanup
kill $API_PID $WORKER_PID $OUTREACH_PID 2>/dev/null || true
echo "✅ Real API integration test complete"
```

---

## Risk Mitigation

### Fallback Strategy
- **Always keep mock mode functional** - If real API fails, gracefully degrade to mock
- **Rate limiting** - Implement backoff for 429 responses
- **Timeouts** - Set aggressive timeouts (10s) to prevent hanging workers
- **Error logging** - Send all API failures to Sentry for monitoring

### API Quota Management
```python
# Track API usage to avoid overages
class APIQuotaTracker:
    def __init__(self):
        self.stackai_calls = 0
        self.truefoundry_calls = 0
        self.lightfield_calls = 0

    def check_quota(self, service: str) -> bool:
        # Implement daily/hourly limits
        if service == "stackai" and self.stackai_calls > 1000:
            logger.warning("stackAI quota exceeded, using mock")
            return False
        return True
```

---

## Success Criteria

### Phase 1: stackAI
- [ ] Real API call succeeds with valid API key
- [ ] Lead receives score between 0-1
- [ ] Persona correctly assigned (enterprise/smb)
- [ ] Graceful fallback to mock on API failure

### Phase 2: Truefoundry
- [ ] Real AI generates personalized subject + body
- [ ] Message includes lead-specific details
- [ ] Tone matches experiment configuration
- [ ] Fallback to template rendering on API failure

### Phase 3: Lightfield
- [ ] Real email sent to recipient
- [ ] Message ID returned for tracking
- [ ] Webhook receives engagement events
- [ ] Outreach logs updated with delivery status

### End-to-End
- [ ] Single lead flows through all 3 APIs successfully
- [ ] No worker crashes or timeouts
- [ ] Dashboard reflects real outreach data
- [ ] Sentry reports no critical errors

---

## Rollout Plan

### Step 1: Gradual Rollout
1. ✅ Create `feat/real-api-integration` branch
2. Integrate stackAI first (lowest risk - Phase 1 only)
3. Test thoroughly, commit
4. Integrate Truefoundry (Phase 2)
5. Test, commit
6. Integrate Lightfield (highest risk - actually sends emails!)
7. Test with whitelisted recipients only

### Step 2: Parallel Testing
- Run **both** mock and real modes simultaneously
- Compare results for consistency
- Use feature flag: `USE_REAL_APIS=true/false`

### Step 3: Demo Preparation
- Keep `feat/phase4-demo-ui` branch as **stable demo** (mock mode)
- Use `feat/real-api-integration` for **live judging** (real APIs)
- Judges see actual AI-generated content, real email IDs

---

## Open Questions for Hackathon Team

1. **stackAI**:
   - What is the exact API endpoint for lead scoring?
   - Do we have a trained model/project already deployed?
   - What input features does the model expect?

2. **Truefoundry**:
   - Is there a deployed agent/endpoint for personalization?
   - What is the workspace ID we should use?
   - Are there token limits per request?

3. **Lightfield**:
   - Do we have a verified sender domain configured?
   - What email address should we send from?
   - Should we use sandbox mode for testing or real sends?

4. **Demo Strategy**:
   - Should we use real APIs for the final presentation?
   - Or keep mock mode for reliability and speed?
   - Do judges expect to see real API calls in action?

---

## Files to Create/Modify

### New Files
- [ ] `apps/agent-api/app/services/stackai_client.py`
- [ ] `apps/agent-api/app/routes/webhooks.py`
- [ ] `scripts/test-real-apis.sh`
- [ ] `tests/test_stackai_client.py`
- [ ] `tests/test_truefoundry_client.py`
- [ ] `tests/test_lightfield_client.py`
- [ ] `docs/real-api-credentials.md` (private, not committed)

### Modified Files
- [ ] `services/workers/lead_scorer_worker.py` (use real stackAI)
- [ ] `apps/agent-api/app/services/truefoundry_client.py` (test real endpoint)
- [ ] `apps/agent-api/app/services/lightfield_client.py` (remove simulation flag)
- [ ] `apps/agent-api/app/config/settings.py` (add new env vars)
- [ ] `.env.example` (document real API configuration)
- [ ] `apps/agent-api/main.py` (register webhook routes)

---

## Timeline (Estimated)

| Task | Time | Status |
|------|------|--------|
| Research API endpoints | 1 hour | ⏳ Pending |
| Implement stackAI client | 2 hours | ⏳ Pending |
| Test stackAI integration | 1 hour | ⏳ Pending |
| Implement Truefoundry updates | 2 hours | ⏳ Pending |
| Test Truefoundry integration | 1 hour | ⏳ Pending |
| Implement Lightfield webhooks | 2 hours | ⏳ Pending |
| Test Lightfield integration | 1 hour | ⏳ Pending |
| End-to-end testing | 2 hours | ⏳ Pending |
| **Total** | **12 hours** | |

---

## Next Steps

1. **Immediate:** Gather real API credentials from hackathon sponsors
2. **Research:** Read API documentation for all 3 services
3. **Test:** Make curl requests to verify endpoints before coding
4. **Implement:** Follow checklist top-to-bottom
5. **Validate:** Run test scripts after each integration
6. **Demo:** Decide mock vs real for presentation

---

**Created:** 2025-10-17
**Branch:** `feat/real-api-integration`
**Status:** Planning Phase
