# ✅ Stack AI Integration Complete!

**Status:** Ready to test with real API key
**Branch:** `feat/real-api-integration`
**Date:** 2025-10-17

---

## What We Built

### 1. **Production Stack AI Client**
**File:** `apps/agent-api/app/services/stackai_client.py`

**Features:**
- ✅ Real API calls to your deployed Stack AI workflow
- ✅ Automatic fallback to mock mode if API fails
- ✅ Smart response parsing (handles JSON, wrapped responses, markdown)
- ✅ Error handling with detailed logging
- ✅ Health check endpoint
- ✅ Singleton pattern for efficiency

**Your Stack AI Workflow:**
```
Endpoint: https://api.stack-ai.com/inference/v0/run/f3d287f4-b108-4ce6-80ac-e7a8121e59ec/68f2b44f9dce4066a0ab4058
Org ID:   f3d287f4-b108-4ce6-80ac-e7a8121e59ec
Flow ID:  68f2b44f9dce4066a0ab4058
Model:    GPT-4o Mini (via Stack AI)
```

---

### 2. **Updated Lead Scorer Worker**
**File:** `services/workers/lead_scorer_worker.py`

**Changes:**
- ✅ Replaced mock scoring with real Stack AI client
- ✅ Maps Lightfield data to Stack AI format
- ✅ Converts employee size ranges to numbers (e.g., "201-1000" → 600)
- ✅ Estimates revenue from budget ranges
- ✅ Health check on worker startup
- ✅ Still has mock fallback for demo reliability

---

### 3. **Test Script**
**File:** `scripts/test-stackai-integration.sh`

**What It Tests:**
- ✅ Environment variables configured
- ✅ Stack AI client import
- ✅ Health check (mock vs real API)
- ✅ Enterprise lead scoring
- ✅ SMB lead scoring
- ✅ High-value enterprise scoring
- ✅ Persona classification accuracy
- ✅ Score ordering validation

---

## How To Use It

### **Step 1: Add Your Private API Key**

Open `apps/agent-api/.env` and replace:
```bash
STACKAI_API_KEY=YOUR_PRIVATE_API_KEY_HERE
```

With your actual private API key from the Stack AI dashboard (the one that was hidden with dots ••••).

**How to get it:**
1. Go to Stack AI dashboard
2. Click on your profile → API Keys
3. Find the "hackathon-api" key
4. Click the eye icon (👁️) to reveal the private key
5. Copy it
6. Paste it in the `.env` file

---

### **Step 2: Run the Test Script**

```bash
cd /Users/bishnubista/Projects/hackathon/pipeline-whisperer-agent
./scripts/test-stackai-integration.sh
```

**Expected Output (if API key is correct):**

```
==============================================================================
STACK AI INTEGRATION TEST
==============================================================================

Step 1: Checking environment variables...
✅ Environment variables configured

Step 2: Testing Stack AI client import...
✓ Import successful
✅ Stack AI client imported

Step 3: Running Stack AI health check...
Status: healthy
Accessible: True
Message: Stack AI API responding
Test score: 0.75

✅ Stack AI is HEALTHY
✅ Health check passed

Step 4: Scoring test leads...

📊 Test 1: Enterprise Lead
--------------------------------------------------
Company: MegaRetail Co
Score: 0.92
Persona: enterprise
Reasoning: Large retail company with 1200 employees and $25M revenue
Is Mock: False

📊 Test 2: SMB Lead
--------------------------------------------------
Company: StartupHub
Score: 0.68
Persona: smb
Reasoning: Small tech startup with 15 employees and $500K revenue
Is Mock: False

📊 Test 3: High-Value Enterprise
--------------------------------------------------
Company: CloudScale Systems
Score: 0.94
Persona: enterprise
Reasoning: Large technology company with 850 employees and $45M revenue
Is Mock: False

==================================================
VALIDATION
==================================================
✅ All scores from REAL Stack AI API
✅ Persona classification looks correct
✅ Score ordering makes sense (high-value > startup)

✅ Lead scoring tests passed

==============================================================================
✅ STACK AI INTEGRATION TEST COMPLETE
==============================================================================
```

---

### **Step 3: Test End-to-End (Optional)**

Once the Stack AI integration test passes, you can test the full pipeline:

```bash
./scripts/test-phase1-standalone.sh
```

This will:
1. Publish a test lead to Kafka
2. Lead scorer worker picks it up
3. Stack AI scores the lead (real API!)
4. Lead is saved to database
5. Dashboard shows the scored lead

---

## What If It Doesn't Work?

### **Problem: Test shows "MOCK MODE"**

**Symptom:**
```
⚠️  Stack AI is in MOCK MODE
Check that your .env has:
  - STACKAI_API_KEY (private key)
  - STACKAI_ORG_ID
  - STACKAI_FLOW_ID
```

**Solution:**
1. Check `apps/agent-api/.env` file exists
2. Verify `STACKAI_API_KEY` is set (not "YOUR_PRIVATE_API_KEY_HERE")
3. Verify it's the **private key**, not the public key
4. Check no typos in org_id or flow_id

---

### **Problem: "HTTP 404" or "HTTP 401" Error**

**Symptom:**
```
❌ Stack AI API error (status 404)
```

**Solutions:**
- **404:** Flow ID is wrong or workflow not deployed
  - Go to Stack AI, check if workflow is deployed
  - Verify flow_id matches the one shown in Stack AI
- **401:** API key is wrong
  - Double-check you're using the **private key**
  - Regenerate API key if needed

---

### **Problem: "Invalid JSON response"**

**Symptom:**
```
Could not parse Stack AI response: ...
Using mock scoring as fallback
```

**Solutions:**
1. Check Stack AI workflow output format
2. Ensure LLM is returning raw JSON (no markdown)
3. Update system prompt to be more explicit about JSON format
4. Check the logs for the actual response:
   ```bash
   tail -f /tmp/pipeline-api.log
   ```

---

## Files Changed

| File | Status | Lines Changed |
|------|--------|---------------|
| `app/services/stackai_client.py` | ✨ New | +400 |
| `services/workers/lead_scorer_worker.py` | 📝 Modified | +60 |
| `app/config/settings.py` | 📝 Modified | +4 |
| `.env.example` | 📝 Modified | +2 |
| `scripts/test-stackai-integration.sh` | ✨ New | +200 |

---

## Configuration Summary

### **Environment Variables Required:**

```bash
# In apps/agent-api/.env
STACKAI_API_KEY=your_private_key_here
STACKAI_ORG_ID=f3d287f4-b108-4ce6-80ac-e7a8121e59ec
STACKAI_FLOW_ID=68f2b44f9dce4066a0ab4058
STACKAI_BASE_URL=https://api.stack-ai.com
```

### **Current Status:**

- ✅ Org ID configured
- ✅ Flow ID configured
- ⏳ **Waiting for you to add STACKAI_API_KEY**

---

## Next Steps

### **Immediate (5 minutes):**
1. ✅ Add your private API key to `apps/agent-api/.env`
2. ✅ Run `./scripts/test-stackai-integration.sh`
3. ✅ Verify all tests pass with "Is Mock: False"

### **After Tests Pass:**
4. ⏳ Run end-to-end test: `./scripts/test-phase1-standalone.sh`
5. ⏳ Start the demo dashboard: `./scripts/start-demo.sh`
6. ⏳ Watch real AI scoring in action!

### **Optional (Future):**
- Integrate Truefoundry for AI personalization
- Integrate Lightfield for real email sending
- Add webhook handlers for engagement tracking

---

## Architecture Diagram

```
┌─────────────┐
│  Lightfield │  Lead data (company, size, budget)
│  (Incoming) │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Kafka     │  leads.raw topic
│  (Redpanda) │
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│ Lead Scorer Worker      │
│  - Consumes leads.raw   │
│  - Calls Stack AI API   │ ─────►  Stack AI Workflow (GPT-4o Mini)
│  - Saves to database    │                │
└──────┬──────────────────┘                │
       │                            ◄───────┘
       │                       {score, persona, reasoning}
       ▼
┌─────────────┐
│  Database   │  leads table (with AI scores!)
│  (SQLite)   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Dashboard  │  Shows real AI-generated scores
│  (Next.js)  │
└─────────────┘
```

---

## Demo Script (for Judges)

**"Watch our autonomous GTM agent score leads in real-time using Stack AI:"**

1. **Open dashboard:** http://localhost:3000
2. **Inject a test lead:** Run `scripts/demo.sh`
3. **Watch it flow:**
   - Lead appears in "Raw Leads" (26)
   - Stack AI scores it in ~2 seconds
   - Score appears (0.0-1.0)
   - Persona assigned (enterprise/smb)
   - AI reasoning shown
4. **Show the magic:** "This isn't mock data - it's real GPT-4o Mini via Stack AI!"
5. **Point out:** Thompson Sampling uses these scores to select best outreach experiments

---

## Troubleshooting Checklist

- [ ] `.env` file exists in `apps/agent-api/`
- [ ] `STACKAI_API_KEY` is set (not placeholder)
- [ ] API key is the **private key** (not public)
- [ ] `STACKAI_ORG_ID` matches Stack AI dashboard
- [ ] `STACKAI_FLOW_ID` matches Stack AI dashboard
- [ ] Stack AI workflow is deployed (not just saved)
- [ ] Stack AI workflow returns JSON format
- [ ] Test script is executable (`chmod +x`)
- [ ] Python virtual environment is activated

---

## Success Criteria

When the integration is working, you'll see:

✅ **Health check:** Status = "healthy"
✅ **Test scores:** Is Mock = False
✅ **Persona classification:** Enterprise leads → "enterprise"
✅ **Score ordering:** High-value companies > Startups
✅ **AI reasoning:** Actual explanations (not "Simple scoring logic")
✅ **Dashboard:** Real scores displayed

---

## Questions?

**Q: How do I get my private API key?**
A: Stack AI dashboard → API Keys → Click eye icon on "hackathon-api"

**Q: Can I use the public key instead?**
A: No, you need the private key for server-side API calls

**Q: What if I regenerate the API key?**
A: Update the `.env` file with the new key, org_id and flow_id stay the same

**Q: How do I know if it's using real API vs mock?**
A: Check the test output for "Is Mock: False" or "Is Mock: True"

**Q: Will this work without internet?**
A: No, it needs to call Stack AI API. Mock mode works offline.

---

**Ready to test?** Add your API key and run the test script! 🚀
