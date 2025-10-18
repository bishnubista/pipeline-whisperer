## Pipeline Whisperer Delivery Plan

### Phase 0 — Foundations & Tool Access
- **Goals**: Agree on architecture, secure sponsor credentials, and bootstrap repo scaffolding.
- **Tasks (TODO)**:
  - Capture API keys/secrets for Lightfield, OpenAI, Truefoundry, Redpanda (cloud/local), and Sentry.
  - Scaffold Next.js app (`apps/web`) and FastAPI service (`apps/agent-api`), each with Sentry instrumentation.
  - Spin up Redpanda locally via Docker Compose and verify Kafka topics (`leads.raw`, `leads.scored`, `outreach.events`).
- **Validation**: `uvicorn` health endpoint returns 200; Redpanda topics visible via `rpk topic list`; Sentry receives a test event from both services.

### Phase 1 — Lead Ingestion & Scoring
- **Goals**: Stream Lightfield events into Redpanda and produce scored leads using OpenAI.
- **Tasks (TODO)**:
  - Implement webhook or simulator that writes Lightfield lead payloads to `leads.raw`.
  - Build Redpanda consumer in FastAPI worker to normalize events and call OpenAI for scoring + persona classification.
  - Persist scored leads in PostgreSQL with status metadata and experiment IDs.
- **Validation**: Publishing a sample lead results in a database record with OpenAI score and persona within seconds; metrics visible in Sentry.

### Phase 2 — Outreach Orchestration
- **Goals**: Launch personalized outreach via Truefoundry-hosted micro-agents and Lightfield actions.
- **Tasks (TODO)**:
  - Define outreach templates/experiments and store them in the agent service.
  - Integrate Truefoundry API to deploy/run outreach jobs that call Lightfield messaging endpoints.
  - Emit outreach status events to Redpanda (`outreach.events`) for observability.
- **Validation**: Triggering a scored lead produces an outreach job, confirmed by Lightfield API response and event in Redpanda/Sentry.

### Phase 3 — Feedback Loop & Learning
- **Goals**: Capture engagement outcomes, update playbooks, and feed telemetry into Sentry.
- **Tasks (TODO)**:
  - Consume Lightfield engagement callbacks (opens, replies, conversions) and push them to Redpanda.
  - Update experiment weights/priors based on outcome metrics (e.g., Thompson Sampling for subject lines).
  - Instrument Sentry with custom metrics/tags for each experiment iteration.
- **Validation**: Simulated conversion updates the lead record, adjusts experiment weights, and logs a Sentry event with new performance stats.

### Phase 4 — Demo Experience & Controls
- **Goals**: Deliver a polished UI and demo script highlighting autonomy.
- **Tasks (TODO)**:
  - Build Next.js dashboard showing real-time pipeline (raw leads, scored leads, outreach, conversions) via websockets or polling.
  - Add manual override controls (snooze lead, force outreach) to illustrate human-in-the-loop fallback.
  - Prepare replay scripts for consistent demo scenarios.
- **Validation**: Running `scripts/demo.sh` populates the dashboard end-to-end; UI updates without manual refresh; override actions propagate to the backend.

### Phase 5 — Polish, Testing & Presentation
- **Goals**: Ensure reliability, finalize storytelling, and package the submission.
- **Tasks (TODO)**:
  - Write integration tests for ingestion → scoring → outreach path (pytest + Playwright for UI smoke).
  - Record demo walkthrough, produce slides, and rehearse 3-minute pitch referencing the sponsor tools.
  - Add README setup commands, environment samples, and troubleshooting tips.
- **Validation**: All tests green in CI (or local run), recorded demo hits the autonomy loop in under 3 minutes, and README instructions reproduce the flow on a fresh machine.
