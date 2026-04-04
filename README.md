# ASIS — Autonomous Strategic Intelligence System v3.0

> Board-level strategic decision intelligence for multinational corporations, powered by a multi-agent LLM pipeline with persistent memory, vector search, and automated workflows.

**Version:** 3.0.0 | **Stack:** Python · FastAPI · LangGraph · Next.js 14 · PostgreSQL · Redis · Qdrant · LiteLLM · n8n

---

## Architecture

```
 ┌────────────────────────────────────────────────────────────────────────────┐
 │                        ASIS v3.0 — System Architecture                     │
 │                                                                            │
 │  LAYER 1 — CLIENT                                                          │
 │  ┌──────────────────────────────────────────────────────────────────────┐  │
 │  │  Next.js 14 Dashboard  (port 3000)                                   │  │
 │  │  AgentStatusPanel · StrategyBrief · RiskMatrix · ExportControls      │  │
 │  └────────────────────┬─────────────────────────────────────────────────┘  │
 │                       │ SSE stream + REST                                  │
 │  LAYER 2 — API GATEWAY                                                     │
 │  ┌──────────────────────────────────────────────────────────────────────┐  │
 │  │  FastAPI (port 8000) · JWT Auth · SlowAPI rate-limit · OTEL tracing  │  │
 │  └────────────────────┬─────────────────────────────────────────────────┘  │
 │                       │                                                    │
 │  LAYER 3 — AGENT PIPELINE (LangGraph StateGraph)                           │
 │  ┌──────────────────────────────────────────────────────────────────────┐  │
 │  │                                                                      │  │
 │  │  START → [Orchestrator] ──────────────────────────────────────────┐  │  │
 │  │                │                                                  │  │  │
 │  │         ┌──────┴───────────────────────┐                          │  │  │
 │  │         ▼              ▼               ▼                          │  │  │
 │  │  [Market Intel]  [Risk Assess]  [Competitor]  (parallel)          │  │  │
 │  │         └──────┬───────────────────────┘                          │  │  │
 │  │                ▼                                                  │  │  │
 │  │       [Financial Reasoning] ──────────────────────────────────────┘  │  │
 │  │                ▼                                                      │  │
 │  │          [Synthesis Agent]                                            │  │
 │  │                ▼                                                      │  │
 │  │          StrategicBrief JSON                                          │  │
 │  └──────────────────────────────────────────────────────────────────────┘  │
 │                                                                            │
 │  LAYER 4 — LLM PROXY                                                       │
 │  ┌──────────────────────────────────────────────────────────────────────┐  │
 │  │  LiteLLM (port 4000) · claude-sonnet-4-5 · claude-haiku-4-5         │  │
 │  │  text-embedding-3-small · Master key auth                            │  │
 │  └──────────────────────────────────────────────────────────────────────┘  │
 │                                                                            │
 │  LAYER 5 — MEMORY & VECTOR STORE                                           │
 │  ┌───────────────────────┐  ┌────────────────────────────────────────────┐ │
 │  │  Qdrant (port 6333)   │  │  Mem0 — persistent cross-session memory    │ │
 │  │  Semantic search      │  │  User context + company profiles           │ │
 │  └───────────────────────┘  └────────────────────────────────────────────┘ │
 │                                                                            │
 │  LAYER 6 — TASK QUEUE                                                      │
 │  ┌──────────────────────────────────────────────────────────────────────┐  │
 │  │  Celery Worker · Redis broker (db 1) · Redis result backend (db 2)   │  │
 │  └──────────────────────────────────────────────────────────────────────┘  │
 │                                                                            │
 │  LAYER 7 — WORKFLOW AUTOMATION                                             │
 │  ┌──────────────────────────────────────────────────────────────────────┐  │
 │  │  n8n (port 5678) · Scheduled intelligence briefs · Webhook triggers  │  │
 │  │  Report delivery · Slack/email notifications                         │  │
 │  └──────────────────────────────────────────────────────────────────────┘  │
 │                                                                            │
 │  LAYER 8 — PERSISTENCE                                                     │
 │  ┌───────────────────────────┐  ┌─────────────────────────────────────┐    │
 │  │  PostgreSQL 16 (port 5432)│  │  Redis 7 (port 6379)                │    │
 │  │  Users · Analyses · Reports│  │  Cache · Rate limits · Sessions     │    │
 │  └───────────────────────────┘  └─────────────────────────────────────┘    │
 │                                                                            │
 │  LAYER 9 — OBSERVABILITY                                                   │
 │  ┌──────────────────────────────────────────────────────────────────────┐  │
 │  │  Langfuse (port 3001) · LLM trace logging · Token usage · Latency   │  │
 │  │  OpenTelemetry SDK · OTLP exporter · structlog                       │  │
 │  └──────────────────────────────────────────────────────────────────────┘  │
 └────────────────────────────────────────────────────────────────────────────┘
```

### Agent Responsibilities

| Agent | Role | Tools |
|---|---|---|
| **Orchestrator** | Query classification, execution planning, context routing | — |
| **Market Intelligence** | Market sizing, trend analysis, regulatory landscape | Tavily, NewsAPI |
| **Risk Assessment** | Geopolitical, regulatory, and operational risk register | NewsAPI, Tavily |
| **Financial Reasoning** | Cost modelling, ROI projections, peer benchmarking | FMP API |
| **Competitor Analysis** | Porter Five Forces, competitor profiling | Tavily, NewsAPI |
| **Synthesis** | Board-ready strategic brief integration | — |

---

## Project Structure

```
Strategic-Decision-Maker/
├── asis/
│   ├── backend/
│   │   ├── agents/           # 6 specialist agents + base class + Pydantic schemas
│   │   ├── graph/            # LangGraph StateGraph + AgentState TypedDict
│   │   ├── mcp/              # Web search, financial data, news, Drive wrappers
│   │   ├── api/              # FastAPI routes (analysis, reports, auth, health)
│   │   ├── db/               # SQLAlchemy ORM + Alembic migrations
│   │   ├── memory/           # Mem0 integration + Qdrant vector ops
│   │   ├── tasks/            # Celery task definitions + celery_app factory
│   │   ├── evaluation/       # EvaluationEngine + SingleAgentBaseline
│   │   ├── config/           # Pydantic Settings + structlog configuration
│   │   ├── schemas/          # Shared Pydantic schemas
│   │   ├── tests/            # pytest test suite
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── frontend/
│   │   ├── app/              # Next.js 14 App Router pages
│   │   ├── components/       # AgentStatusPanel, StrategyBrief, RiskMatrix
│   │   └── lib/              # API client + SSE stream utilities
│   ├── n8n/
│   │   ├── Dockerfile        # n8n custom image with pre-installed nodes
│   │   └── workflows/        # Exported n8n workflow JSON files
│   └── infra/
│       ├── cloudbuild/
│       │   ├── cloudbuild.backend.yaml
│       │   └── cloudbuild.frontend.yaml
│       └── terraform/
│           ├── main.tf       # VPC, Cloud SQL, Redis, Cloud Run services
│           ├── variables.tf
│           ├── outputs.tf
│           ├── secret_manager.tf
│           └── iam.tf
├── .github/
│   └── workflows/
│       ├── ci.yml            # PR lint + test pipeline
│       └── deploy.yml        # Push-to-main Cloud Build trigger
├── docker-compose.yml        # Full local dev stack (9 services)
├── litellm_config.yaml       # LiteLLM model routing configuration
└── .env.example              # All environment variables with descriptions
```

---

## Local Development Setup

### Prerequisites

- Docker Desktop 4.x+ (recommended) **or** Python 3.11+, Node 20+, PostgreSQL 16+
- An [Anthropic API key](https://console.anthropic.com)

### 1. Clone and configure

```bash
git clone https://github.com/akshatb848/strategic-decision-maker.git
cd Strategic-Decision-Maker
cp .env.example .env
# Edit .env — add ANTHROPIC_API_KEY and JWT_SECRET at minimum
```

### 2. Start the full stack

```bash
docker compose up --build
```

Services will start in dependency order. Wait ~60 seconds for all health checks to pass.

| Service | URL | Description |
|---|---|---|
| Backend API | http://localhost:8000 | FastAPI application |
| API Docs | http://localhost:8000/api/docs | Swagger UI |
| Frontend | http://localhost:3000 | Next.js dashboard |
| Langfuse | http://localhost:3001 | LLM observability |
| n8n | http://localhost:5678 | Workflow automation |
| LiteLLM | http://localhost:4000 | LLM proxy |
| Qdrant | http://localhost:6333 | Vector store UI |

### 3. Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

### 4. Without Docker (manual)

**Backend:**
```bash
cd asis/backend
pip install -r requirements.txt
createdb asis
alembic upgrade head
uvicorn asis.backend.api.main:app --reload --port 8000
```

**Celery worker (separate terminal):**
```bash
cd asis/backend
celery -A asis.backend.tasks.celery_app worker --loglevel=info
```

**Frontend:**
```bash
cd asis/frontend
npm install
npm run dev
```

---

## GCP Deployment Guide

### Prerequisites

- GCP project with billing enabled
- `gcloud` CLI authenticated (`gcloud auth login`)
- Terraform >= 1.6 installed
- Artifact Registry repository named `asis` created in your project

### 1. Provision infrastructure with Terraform

```bash
cd asis/infra/terraform

# Initialise — uses GCS backend (bucket: asis-tf-state)
terraform init

# Preview changes
terraform plan \
  -var="project_id=YOUR_PROJECT_ID" \
  -var="environment=prod" \
  -var="db_password=YOUR_SECURE_PASSWORD"

# Apply
terraform apply \
  -var="project_id=YOUR_PROJECT_ID" \
  -var="environment=prod" \
  -var="db_password=YOUR_SECURE_PASSWORD"
```

### 2. Populate Secret Manager secrets

```bash
# Set each secret value (repeat for all secrets)
echo -n "sk-ant-api03-..." | \
  gcloud secrets versions add ANTHROPIC_API_KEY --data-file=-

echo -n "postgresql+asyncpg://asis:PASS@/asis?host=/cloudsql/PROJECT:REGION:INSTANCE" | \
  gcloud secrets versions add DATABASE_URL --data-file=-

# ... repeat for JWT_SECRET, REDIS_URL, TAVILY_API_KEY, FMP_API_KEY,
#     NEWSAPI_KEY, LITELLM_MASTER_KEY, N8N_WEBHOOK_SECRET,
#     LANGFUSE_SECRET_KEY, MEM0_API_KEY
```

### 3. Deploy with Cloud Build

```bash
# Deploy backend
gcloud builds submit \
  --config=asis/infra/cloudbuild/cloudbuild.backend.yaml \
  --substitutions=COMMIT_SHA=$(git rev-parse HEAD),_PROJECT_ID=YOUR_PROJECT_ID \
  .

# Deploy frontend
gcloud builds submit \
  --config=asis/infra/cloudbuild/cloudbuild.frontend.yaml \
  --substitutions=COMMIT_SHA=$(git rev-parse HEAD),_PROJECT_ID=YOUR_PROJECT_ID,_NEXT_PUBLIC_API_URL=https://YOUR_BACKEND_URL/api/v1 \
  .
```

### 4. CI/CD (GitHub Actions)

Set the following GitHub repository secrets:

| Secret | Description |
|---|---|
| `GCP_SA_KEY` | JSON key for a GCP service account with Cloud Build Editor and Storage Object Admin roles |
| `GCP_PROJECT_ID` | Your GCP project ID |
| `GCP_REGION` | Deployment region (default: `asia-south1`) |
| `NEXT_PUBLIC_API_URL` | Public URL of the deployed backend |

Pushes to `main` automatically trigger the deploy workflow. PRs to `main` run lint and tests.

---

## API Reference

All endpoints (except `/v1/health`) require `Authorization: Bearer <jwt_token>`.

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Register a new user account |
| `POST` | `/api/v1/auth/login` | Obtain a JWT access token |
| `GET` | `/api/v1/auth/me` | Get current authenticated user info |
| `POST` | `/api/v1/auth/refresh` | Refresh JWT token |

### Analysis

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/analysis` | Trigger ASIS multi-agent pipeline (SSE stream) |
| `GET` | `/api/v1/analysis/{id}` | Retrieve analysis details and agent status |
| `GET` | `/api/v1/analysis` | List paginated analysis history |

#### POST /api/v1/analysis — Request body

```json
{
  "query": "Should we enter the Indian fintech market in 2026?",
  "company_context": {
    "company_name": "Acme Financial",
    "sector": "Financial Services",
    "target_market": "India",
    "hq_country": "United Kingdom",
    "annual_revenue_usd_mn": 850
  },
  "options": {
    "run_baseline": false,
    "agents": ["market_intelligence", "risk_assessment", "financial_reasoning", "competitor_analysis"]
  }
}
```

#### SSE events streamed

```
event: agent_start        data: {"agent": "orchestrator"}
event: agent_complete     data: {"agent": "orchestrator", "duration_ms": 3200}
event: agent_start        data: {"agent": "market_intelligence"}
event: agent_complete     data: {"agent": "market_intelligence", "duration_ms": 8100}
event: agent_start        data: {"agent": "risk_assessment"}
event: agent_complete     data: {"agent": "risk_assessment", "duration_ms": 7200}
event: agent_start        data: {"agent": "financial_reasoning"}
event: agent_complete     data: {"agent": "financial_reasoning", "duration_ms": 5400}
event: agent_start        data: {"agent": "competitor_analysis"}
event: agent_complete     data: {"agent": "competitor_analysis", "duration_ms": 6800}
event: agent_start        data: {"agent": "synthesis"}
event: agent_complete     data: {"agent": "synthesis", "duration_ms": 4100}
event: analysis_complete  data: {"analysis_id": "uuid", "strategic_brief": {...}}
```

### Reports

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/reports` | Paginated list of strategic briefs (`?page=1&page_size=20`) |
| `GET` | `/api/v1/reports/{id}` | Full StrategicBrief JSON |
| `GET` | `/api/v1/reports/{id}/evaluation` | Evaluation scores vs baseline |
| `DELETE` | `/api/v1/reports/{id}` | Delete a report |

### Memory

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/memory` | Retrieve user memory context |
| `DELETE` | `/api/v1/memory` | Clear user memory |

### System

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/v1/health` | None | System health check (all services) |
| `GET` | `/v1/metrics` | Admin | Prometheus metrics |

---

## n8n Workflow Guide

n8n runs at http://localhost:5678 (admin / changeme by default — change in `.env`).

### Pre-built Workflows

Workflow JSON files are in `asis/n8n/workflows/` and are auto-loaded on startup.

| Workflow | Trigger | Description |
|---|---|---|
| `scheduled_brief.json` | Daily cron (09:00 UTC) | Runs analysis for configured watchlist companies |
| `webhook_trigger.json` | HTTP webhook | Triggers analysis from external systems |
| `report_delivery.json` | Analysis complete event | Sends strategic brief via email / Slack |
| `alert_monitor.json` | Hourly cron | Monitors news feeds for high-priority risk signals |

### Calling ASIS from n8n

Use an **HTTP Request** node with:
- **URL:** `http://backend:8000/api/v1/analysis`
- **Method:** POST
- **Headers:** `Authorization: Bearer {{ $env.ASIS_API_KEY }}`
- **Body:** Analysis request JSON (see API Reference above)

### Securing webhooks

Set `N8N_WEBHOOK_SECRET` in `.env`. All incoming webhooks to n8n will validate the `X-Webhook-Secret` header against this value.

---

## Dissertation Evaluation Guide

ASIS includes a built-in evaluation framework for the MSc dissertation's experimental methodology comparing multi-agent vs single-agent performance.

### Evaluation Dimensions

| Dimension | Weight | Description |
|---|---|---|
| `analytical_depth` | 25% | Breadth and depth of factors considered |
| `factual_accuracy` | 25% | Sources cited vs claims made ratio |
| `contextual_relevance` | 20% | Alignment to query and company context |
| `actionability` | 20% | Quality and specificity of recommended next steps |
| `internal_consistency` | 10% | Coherence and absence of contradictions across sections |

### Running Evaluations

**Trigger evaluation at analysis time:**

Set `run_baseline: true` in the analysis request options. This runs both the full multi-agent pipeline and a single-agent baseline in parallel, then scores both.

**Retrieve evaluation results:**

```bash
GET /api/v1/reports/{analysis_id}/evaluation
```

Response includes:
```json
{
  "multi_agent_score": 0.87,
  "baseline_score": 0.61,
  "delta": 0.26,
  "dimension_scores": {
    "multi_agent": { "analytical_depth": 0.91, "factual_accuracy": 0.88, ... },
    "baseline":    { "analytical_depth": 0.62, "factual_accuracy": 0.58, ... }
  }
}
```

### Running the Evaluation Test Suite

```bash
cd asis/backend
pytest tests/evaluation/ -v --tb=short
```

---

## Running Tests

```bash
cd asis/backend
pip install -r requirements.txt
pytest tests/ -v --cov=asis/backend --cov-report=term-missing
```

For CI (SQLite in-memory, no external services):

```bash
DATABASE_URL="sqlite+aiosqlite:///:memory:" \
JWT_SECRET="test-secret-32-chars-minimum-len" \
ANTHROPIC_API_KEY="sk-ant-test" \
pytest tests/ -v
```

---

## Environment Variables Reference

| Variable | Required | Description | Example |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API key via LiteLLM | `sk-ant-api03-...` |
| `OPENAI_API_KEY` | Yes | OpenAI key for embeddings | `sk-...` |
| `JWT_SECRET` | Yes | JWT signing secret (min 32 chars) | `random-32-char-string` |
| `DATABASE_URL` | Yes | PostgreSQL async connection string | `postgresql+asyncpg://asis:asis@localhost:5432/asis` |
| `REDIS_URL` | Yes | Redis connection URL | `redis://localhost:6379/0` |
| `LITELLM_PROXY_URL` | Yes | LiteLLM proxy base URL | `http://localhost:4000` |
| `LITELLM_MASTER_KEY` | Yes | LiteLLM authentication key | `sk-dev-master-key` |
| `QDRANT_URL` | Yes | Qdrant vector store URL | `http://localhost:6333` |
| `QDRANT_API_KEY` | No | Qdrant API key (blank for local) | — |
| `MEM0_API_KEY` | No | Mem0 persistent memory API key | `m0-...` |
| `MEM0_BASE_URL` | No | Mem0 base URL | `https://api.mem0.ai` |
| `LANGFUSE_PUBLIC_KEY` | No | Langfuse public key for tracing | `pk-lf-...` |
| `LANGFUSE_SECRET_KEY` | No | Langfuse secret key (server only) | `sk-lf-...` |
| `LANGFUSE_HOST` | No | Langfuse host URL | `http://localhost:3001` |
| `TAVILY_API_KEY` | No | Tavily web search API key | `tvly-...` |
| `FMP_API_KEY` | No | Financial Modeling Prep key | `abc123...` |
| `NEWSAPI_KEY` | No | NewsAPI key for news context | `abc123...` |
| `N8N_WEBHOOK_SECRET` | No | Shared secret for n8n webhooks | `random-secret` |
| `CELERY_BROKER_URL` | No | Celery broker (Redis db 1) | `redis://localhost:6379/1` |
| `CELERY_RESULT_BACKEND` | No | Celery result store (Redis db 2) | `redis://localhost:6379/2` |
| `ALLOWED_ORIGINS` | No | CORS allowed origins | `http://localhost:3000` |
| `ENVIRONMENT` | No | deployment | deployment environment | `development` |
| `GCP_PROJECT_ID` | No | GCP project ID for cloud deploys | `my-gcp-project` |
| `GCP_REGION` | No | GCP region | `asia-south1` |

---

*ASIS v3.0 — MSc International Management, University of Sussex Delhi · Akshat Banga*
