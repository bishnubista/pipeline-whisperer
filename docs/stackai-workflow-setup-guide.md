# Stack AI Lead Scoring Workflow - Setup Guide

**Goal:** Create a workflow that scores leads and classifies them as enterprise or SMB

**Time Required:** ~10 minutes

---

## Step 1: Create New Project

1. Go to Stack AI dashboard
2. Click **"New Project"** button (top left in templates view)
3. You'll see: "Start from scratch. 1 input / 1 output"

---

## Step 2: Configure Workflow Settings

### Basic Info
- **Name:** `Lead Scoring Engine`
- **Description:** `Analyzes company data to generate quality scores and persona classification`
- **Category:** Analytics (optional)

---

## Step 3: Set Up Input Node

Click on the **Input node** in the workflow canvas

### Input Configuration
Set input type to **JSON** with these fields:

```json
{
  "company_name": "",
  "industry": "",
  "employee_count": 0,
  "revenue": 0,
  "website": ""
}
```

**OR** if Stack AI uses sequential inputs:
- **in-0:** `company_name` (Text)
- **in-1:** `industry` (Text)
- **in-2:** `employee_count` (Number)
- **in-3:** `revenue` (Number)
- **in-4:** `website` (Text)

### Example Test Input
```json
{
  "company_name": "TechCorp Inc",
  "industry": "technology",
  "employee_count": 500,
  "revenue": 15000000,
  "website": "techcorp.com"
}
```

---

## Step 4: Add LLM Node

1. Click **"+"** or **"Add Node"** button
2. Select **"LLM"** or **"AI Model"**
3. Choose model: **GPT-4** or **Claude 3.5 Sonnet** (recommended for reasoning)

### LLM Configuration

**Node Name:** `Lead Scorer`

**System Prompt:**
```
You are an expert B2B lead qualification system. Your job is to analyze company information and provide:

1. A quality score from 0.0 to 1.0
2. A persona classification (enterprise or smb)
3. Brief reasoning

Scoring Criteria:
- High Score (0.8-1.0): Large companies, strong revenue, strategic industries
- Medium Score (0.5-0.79): Mid-market companies with growth potential
- Low Score (0.0-0.49): Small companies or low-fit industries

Persona Rules:
- Enterprise: 500+ employees OR $10M+ annual revenue
- SMB: <500 employees AND <$10M annual revenue

Always respond in valid JSON format only, no markdown.
```

**User Prompt:**
```
Analyze this lead and provide scoring:

Company Name: {{company_name}}
Industry: {{industry}}
Employee Count: {{employee_count}}
Annual Revenue: ${{revenue}}
Website: {{website}}

Return ONLY valid JSON (no code blocks):
{
  "score": 0.85,
  "persona": "enterprise",
  "reasoning": "Brief explanation here"
}
```

**OR** if using sequential inputs (in-0, in-1, etc.):
```
Analyze this lead and provide scoring:

Company Name: {{in-0}}
Industry: {{in-1}}
Employee Count: {{in-2}}
Annual Revenue: ${{in-3}}
Website: {{in-4}}

Return ONLY valid JSON (no code blocks):
{
  "score": 0.85,
  "persona": "enterprise",
  "reasoning": "Brief explanation here"
}
```

### LLM Settings
- **Temperature:** `0.3` (consistent scoring)
- **Max Tokens:** `200` (we only need short JSON response)
- **Model:** GPT-4 or Claude 3.5 Sonnet

---

## Step 5: Add JSON Parser Node (Optional but Recommended)

If Stack AI has a JSON parser node:

1. Add **"JSON Parser"** node after LLM
2. Connect LLM output to parser input
3. Extract fields:
   - `score` → number
   - `persona` → string
   - `reasoning` → string

This ensures the output is structured correctly.

---

## Step 6: Configure Output Node

Click on the **Output node**

### Output Configuration

**Output Type:** JSON

**Schema:**
```json
{
  "score": 0.0,
  "persona": "",
  "reasoning": ""
}
```

**OR** if Stack AI uses simple output:
- Map `{{LLM.score}}` to output field `score`
- Map `{{LLM.persona}}` to output field `persona`
- Map `{{LLM.reasoning}}` to output field `reasoning`

---

## Step 7: Test the Workflow

Click **"Test"** or **"Run"** button

### Test Input Data
```json
{
  "company_name": "MegaRetail Co",
  "industry": "retail",
  "employee_count": 1200,
  "revenue": 25000000,
  "website": "megaretail.com"
}
```

### Expected Output
```json
{
  "score": 0.92,
  "persona": "enterprise",
  "reasoning": "Large retail company with 1200 employees and $25M revenue. Strong enterprise fit."
}
```

### Test with SMB Example
```json
{
  "company_name": "StartupHub",
  "industry": "technology",
  "employee_count": 15,
  "revenue": 500000,
  "website": "startuphub.io"
}
```

### Expected Output
```json
{
  "score": 0.68,
  "persona": "smb",
  "reasoning": "Small tech startup with 15 employees and $500K revenue. Growth potential but SMB segment."
}
```

---

## Step 8: Deploy the Workflow

1. Click **"Deploy"** button (usually top right)
2. Confirm deployment
3. Wait for deployment to complete (~30 seconds)

### After Deployment: Copy API Details

You'll see an API endpoint screen with:

**API Endpoint URL:**
```
https://api.stack-ai.com/inference/v0/run/{org_id}/{flow_id}
```

**Example: Your URL might look like:**
```
https://api.stack-ai.com/inference/v0/run/org-abc123xyz/7f8e9d1c-4b5a-6c7d-8e9f-0a1b2c3d4e5f
```

### Extract These Values:

1. **org_id:** The part after `/run/` and before the next `/`
   - Example: `org-abc123xyz`

2. **flow_id:** The UUID or ID after `org_id`
   - Example: `7f8e9d1c-4b5a-6c7d-8e9f-0a1b2c3d4e5f`

3. **API Key:** Use the one from your API keys page:
   - **Public Key:** For client-side (if needed)
   - **Private Key:** For server-side (our backend)

---

## Step 9: Test API with curl

Stack AI should provide a code snippet. Test it:

```bash
curl -X POST https://api.stack-ai.com/inference/v0/run/{YOUR_ORG_ID}/{YOUR_FLOW_ID} \
  -H "Authorization: Bearer YOUR_PRIVATE_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "TechCorp Inc",
    "industry": "technology",
    "employee_count": 500,
    "revenue": 15000000,
    "website": "techcorp.com"
  }'
```

**OR** if Stack AI uses `in-0`, `in-1` format:
```bash
curl -X POST https://api.stack-ai.com/inference/v0/run/{YOUR_ORG_ID}/{YOUR_FLOW_ID} \
  -H "Authorization: Bearer YOUR_PRIVATE_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "in-0": "TechCorp Inc",
    "in-1": "technology",
    "in-2": 500,
    "in-3": 15000000,
    "in-4": "techcorp.com",
    "user_id": "test-user"
  }'
```

### Expected Response
```json
{
  "score": 0.87,
  "persona": "enterprise",
  "reasoning": "Large technology company with 500 employees and $15M revenue"
}
```

---

## Step 10: Provide Integration Details

Once you've tested successfully, send me:

1. ✅ **org_id:** (e.g., `org-abc123xyz`)
2. ✅ **flow_id:** (e.g., `7f8e9d1c-4b5a-6c7d-8e9f-0a1b2c3d4e5f`)
3. ✅ **Input format:** Does it use JSON object or `in-0, in-1` format?
4. ✅ **Private API Key:** (from your API keys page - we'll store in .env)

---

## Troubleshooting

### Issue: "Invalid JSON response"
**Solution:** Make sure the LLM prompt says "Return ONLY valid JSON (no code blocks)"

Add to system prompt:
```
IMPORTANT: Return raw JSON only. Do not wrap in markdown code blocks.
Do not include ```json or ``` tags.
```

### Issue: "Score is always the same"
**Solution:** Lower the temperature to 0.1-0.3 for more consistent results, or raise it to 0.5-0.7 for more variability.

### Issue: "Workflow times out"
**Solution:** Reduce max_tokens to 150 or use a faster model (GPT-3.5-turbo instead of GPT-4)

### Issue: "Persona classification inconsistent"
**Solution:** Add explicit thresholds in the prompt:
```
STRICT RULES:
- If employee_count >= 500 OR revenue >= 10000000: persona = "enterprise"
- Otherwise: persona = "smb"
```

---

## Example Workflow Diagram

```
┌─────────────┐
│   Input     │  company_name, industry, employee_count, revenue, website
│   (JSON)    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  LLM Node   │  GPT-4: Analyze lead, return score + persona
│ (Scorer)    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ JSON Parser │  Extract: score, persona, reasoning
│  (Optional) │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Output    │  { score, persona, reasoning }
│   (JSON)    │
└─────────────┘
```

---

## Next Steps After Deployment

1. ✅ Copy org_id and flow_id
2. ✅ Test with curl command
3. ✅ Verify response format
4. ✅ Send me the details
5. ⏳ I'll integrate into the lead_scorer_worker.py
6. ⏳ We'll test end-to-end with real leads!

---

**Questions?** Take screenshots of any step and share them - I'll help troubleshoot!

**Estimated Time:** 10-15 minutes total
