## Pipeline Whisperer
Autonomous GTM agent for the Context Engineering Hackathon. Pipeline Whisperer streams live Lightfield CRM activity through Redpanda, has stackAI qualify and personalize outreach, executes actions via Truefoundry agents, and closes the loop with conversion telemetry in Sentry. The result is a self-improving revenue engine that continuously experiments, prioritizes high-intent leads, and suppresses ineffective messaging—no human babysitting required.

### Why This Stack
- **Next.js (TypeScript)** for the demo UI and lightweight command center. It ships fast, supports server actions for calling backend APIs, and Sentry/Ligthfield SDKs have first-class TypeScript support.
- **Python + FastAPI** for the agent brain. Sentry, Redpanda (Kafka), stackAI, and Truefoundry all provide mature Python SDKs or REST/GraphQL clients. Python makes it easy to run async consumers, experiment orchestration, and A/B learning loops.
- **Redpanda** for the real-time bus (Kafka-compatible; we can use `confluent-kafka` in Python and `kafkajs` if we need client-side previews).
- **PostgreSQL / SQLite** as lightweight state store for lead status and experiment metadata.
- **Docker Compose** to spin up Redpanda locally and keep the demo reproducible.

This combination minimizes glue work, hits the hackathon autonomy criteria, and lets every sponsor tool shine in a 3-minute demo.

### Version Matrix (lock early to avoid mismatch issues)
| Layer | Package | Version |
|-------|---------|---------|
| Runtime | Node.js | 20.11.1 LTS |
| Runtime | Python | 3.11.8 |
| Frontend | Next.js | 14.2.3 |
| Frontend | React | 18.2.0 |
| Frontend | TypeScript | 5.4.3 |
| Frontend | Sentry Next.js SDK (`@sentry/nextjs`) | 7.114.0 |
| Frontend | Kafka client (`kafkajs`) | 2.2.4 |
| Backend | FastAPI | 0.110.1 |
| Backend | Uvicorn (`uvicorn[standard]`) | 0.29.0 |
| Backend | Pydantic | 2.7.1 |
| Backend | SQLAlchemy | 2.0.29 |
| Backend | PostgreSQL driver (`psycopg[binary]`) | 3.1.18 |
| Backend | Kafka client (`confluent-kafka`) | 2.3.0 |
| Backend | Sentry Python SDK (`sentry-sdk`) | 1.43.1 |
| Backend | HTTP client (`httpx`) | 0.27.0 |
| Sponsor SDK | stackAI Python SDK | 0.5.x (confirm from vendor) |
| Sponsor SDK | Lightfield REST client | latest stable (confirm; likely REST) |
| Sponsor SDK | Truefoundry Python SDK (`truefoundry`) | 0.7.x (confirm from vendor) |
| Tooling | Docker Compose | v2.24.5 |
| Tooling | pnpm | 9.1.1 |

> As soon as credentials land, confirm exact sponsor SDK versions—they ship quickly, so we’ll freeze whichever minor release they recommend and record any API quirks in `docs/integration-notes.md`.

### Sponsor Tool Integration Plan
- **Lightfield CRM**: Webhooks push lead events into Redpanda; outreach actions flow back through Lightfield APIs from Truefoundry agents.
- **stackAI**: Primary reasoning layer; scores and clusters incoming leads, generates outreach prompts, and experiments with variants.
- **Redpanda**: Central event backbone carrying lead events, scoring decisions, and feedback signals.
- **Truefoundry**: Hosts micro-agents that execute outreach (email/slack/in-app) and manage follow-up cadences.
- **Sentry**: Observability + learning store; captures outcomes (opens, conversions, failures) and powers the feedback loop.

### High-Level Architecture
```
Lightfield CRM --> Redpanda --> FastAPI Agent (stackAI scoring, experiment engine)
                                         |
                                         +--> Truefoundry Outreach Agent --> Lightfield Actions
                                         |
                                         +--> Sentry Telemetry (success/failure signals)

FastAPI Agent <--> PostgreSQL (state & experiments)
FastAPI Agent <--> Next.js UI (dashboards, manual overrides)
```

### Demo Script (3 Minutes)
1. Show the Next.js dashboard with an empty lead queue and the sponsor-tool data flow.
2. Inject sample Lightfield lead events (either replay files or simulated webhook) and watch them appear in real time.
3. Highlight stackAI scoring results and how Truefoundry agents launch personalized outreach.
4. Trigger a mock conversion response; Sentry logs it, the agent updates its playbook, and the UI reflects the learning.
5. Conclude with metrics: lead prioritized, outreach sent, conversion captured—all autonomous.

### Repository Layout (planned)
```
/
├── README.md
├── PLAN.md
├── apps/
│   ├── web/           # Next.js frontend
│   └── agent-api/     # FastAPI service (Python)
├── services/
│   ├── workers/       # Redpanda consumers, experiment engine
│   └── simulators/    # Synthetic lead/event generators for demo
├── docker/
│   ├── docker-compose.redpanda.yaml
│   └── Dockerfile.*   # Build images for agent + web
└── scripts/
    ├── seed_leads.py
    └── demo.sh
```

### Setup Outline (to be detailed as code lands)
1. Install dependencies (Node 18+, Python 3.11+, Docker).
2. `docker compose -f docker/docker-compose.redpanda.yaml up` to launch Redpanda locally.
3. Set env vars for Lightfield, stackAI, Truefoundry, and Sentry credentials.
4. Start FastAPI (`uvicorn apps/agent-api/main:app --reload`) and Next.js (`pnpm dev`) once scaffolds exist.
5. Run `scripts/seed_leads.py` to push sample events and verify end-to-end flow.

Detailed commands and deployment instructions will evolve alongside implementation; PLAN.md tracks each phase’s deliverables and validation steps.
