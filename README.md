# ASIS — Autonomous Strategic Intelligence System

> Board-level strategic decision intelligence for multinational corporations, powered by a six-agent LLM pipeline.

**Version:** 1.0.0 | **Stack:** Python · FastAPI · LangGraph · Next.js 14 · PostgreSQL

---

## Architecture

```
User Query
    │
    ▼
┌───────────────────────────────────────────────────────────┐
│                    ASIS LangGraph Pipeline                │
│                                                           │
│  START → [Orchestrator] → ┌─────────────────────────┐    │
│                           │  Market Intelligence    │    │
│                           │  Risk Assessment        │──┐ │
│                           │  Competitor Analysis    │  │ │
│                           └─────────────────────────┘  │ │
│                                 (parallel)              │ │
│                                     ▼                   │ │
│                           [Financial Reasoning] ────────┘ │
│                                     ▼                     │
│                             [Synthesis Agent]             │
│                                     ▼                     │
│                           StrategicBrief JSON             │
└───────────────────────────────────────────────────────────┘
    │
    ▼
FastAPI SSE Stream → Next.js Dashboard
```

### Agent Responsibilities

| Agent | Role | MCP Tools |
|---|---|---|
| **Orchestrator** | Query classification + execution planning | — |
| **Market Intelligence** | Market sizing, trends, regulatory landscape | Tavily, NewsAPI |
| **Risk Assessment** | Geopolitical, regulatory, operational risk register | NewsAPI, Tavily |
| **Financial Reasoning** | Cost modelling, ROI, peer benchmarking | FMP (Yahoo Finance) |
| **Competitor Analysis** | Porter Five Forces + competitor profiling | Tavily, NewsAPI |
| **Synthesis** | Board-ready strategic brief integration | — |

---

## Project Structure

```
asis/
├── backend/
│   ├── agents/           # 6 specialist agents + base class + Pydantic schemas
│   ├── graph/            # LangGraph StateGraph + AgentState TypedDict
│   ├── mcp/              # Web search, financial data, news feed, Drive wrappers
│   ├── api/              # FastAPI routes (analysis, reports, auth, health)
│   ├── db/               # SQLAlchemy ORM + Alembic migrations
│   ├── evaluation/       # EvaluationEngine + SingleAgentBaseline
│   ├── config/           # Pydantic Settings + structlog
│   └── tests/            # pytest tests for schemas + API routes
├── frontend/
│   ├── app/              # Next.js 14 App Router pages
│   ├── components/       # AgentStatusPanel, StrategyBrief, RiskMatrix, ExportControls
│   └── lib/              # API client + SSE stream utilities
├── docker-compose.yml    # Local dev (backend, frontend, postgres, redis)
├── docker-compose.prod.yml
├── railway.toml
└── .env.example
```

---

## Local Setup

### Prerequisites

- Docker Desktop (recommended) **or** Python 3.11+, Node 20+, PostgreSQL 16+
- An [Anthropic API key](https://console.anthropic.com)

### 1. Clone and configure

```bash
git clone https://github.com/akshatb848/strategic-decision-maker.git
cd strategic-decision-maker
cp .env.example .env
# Edit .env — add ANTHROPIC_API_KEY and JWT_SECRET at minimum
```

### 2. Start with Docker (recommended)

```bash
docker-compose up --build
```

- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/api/docs
- **Frontend:** http://localhost:3000

### 3. Without Docker (manual)

**Backend:**
```bash
cd asis/backend
pip install -r requirements.txt
# Create the database
createdb asis
alembic upgrade head
# Run
uvicorn asis.backend.api.main:app --reload --port 8000
```

**Frontend:**
```bash
cd asis/frontend
npm install
npm run dev
```

---

## API Reference

All endpoints (except `/health`) require `Authorization: Bearer <jwt_token>`.

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Register new account |
| `POST` | `/api/v1/auth/login` | Obtain JWT token |
| `GET` | `/api/v1/auth/me` | Current user info |

### Analysis

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/analysis` | Trigger ASIS pipeline (SSE stream) |
| `GET` | `/api/v1/analysis/{id}` | Analysis details + agent status |

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
    "run_baseline": false
  }
}
```

#### SSE Events streamed

```
event: agent_start        data: {"agent": "orchestrator"}
event: agent_complete     data: {"agent": "orchestrator", "duration_ms": 3200}
event: agent_start        data: {"agent": "market_intelligence"}
...
event: analysis_complete  data: {"analysis_id": "...", "strategic_brief": {...}}
```

### Reports

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/reports` | Paginated list (`?page=1&page_size=20`) |
| `GET` | `/api/v1/reports/{id}` | Full StrategicBrief |
| `GET` | `/api/v1/reports/{id}/evaluation` | Evaluation scores |

### System

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/health` | None | System health check |

---

## Railway Deployment

1. **Create a Railway project** and add a PostgreSQL plugin.
2. **Set environment variables** in the Railway dashboard:

   ```
   ANTHROPIC_API_KEY=sk-ant-...
   JWT_SECRET=<random 32+ char string>
   DATABASE_URL=<provided by Railway postgres plugin>
   TAVILY_API_KEY=tvly-...
   FMP_API_KEY=...
   NEWSAPI_KEY=...
   ALLOWED_ORIGINS=https://your-frontend.up.railway.app
   ```

3. **Deploy** — Railway auto-detects `railway.toml` and builds both services.

---

## Evaluation Framework (Dissertation)

ASIS includes a built-in evaluation system for the MSc dissertation's experimental methodology.

Each `StrategicBrief` is scored on:

| Dimension | Weight | Description |
|---|---|---|
| `analytical_depth` | 25% | Breadth of factors considered |
| `factual_accuracy` | 25% | Sources cited vs claims made |
| `contextual_relevance` | 20% | Alignment to query specifics |
| `actionability` | 20% | Next step quality and specificity |
| `internal_consistency` | 10% | Coherence across sections |

**Baseline comparison:** Set `run_baseline: true` in analysis options to also run a single-agent baseline. The `GET /api/v1/reports/{id}/evaluation` endpoint returns both scores and the improvement delta.

---

## Running Tests

```bash
cd asis/backend
pip install -r requirements.txt
pytest tests/ -v
```

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✓ | Claude API key |
| `JWT_SECRET` | ✓ | JWT signing secret (min 32 chars) |
| `DATABASE_URL` | ✓ | PostgreSQL async connection string |
| `TAVILY_API_KEY` | — | Web search (degrades gracefully without) |
| `FMP_API_KEY` | — | Financial data (degrades gracefully) |
| `NEWSAPI_KEY` | — | News context (degrades gracefully) |
| `REDIS_URL` | — | Rate limiting (not required for basic usage) |
| `ALLOWED_ORIGINS` | — | CORS origins (default: localhost:3000) |

---

*ASIS v1.0.0 — MSc International Management, University of Sussex Delhi · Akshat Banga*
