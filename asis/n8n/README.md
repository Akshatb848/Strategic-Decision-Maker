# ASIS n8n Integration

n8n automation layer for the Autonomous Strategic Intelligence System (ASIS) v3.0.

## Setup

### Docker

Build and run the n8n service via the main `docker-compose.yml` in the repo root:

```bash
docker compose up n8n
```

The custom Dockerfile installs `n8n-nodes-langfuse` for Langfuse observability integration.
n8n runs in queue mode backed by Redis (Memorystore in production).

### Environment Variables

Set these in your `.env` or GCP Secret Manager:

| Variable | Description |
|---|---|
| `ASIS_API_URL` | ASIS backend base URL, e.g. `http://asis-backend:8000` |
| `ASIS_WEBHOOK_SECRET` | HMAC-SHA256 secret, must match `N8N_WEBHOOK_SECRET` in ASIS backend |
| `ASIS_DEFAULT_TENANT` | Default tenant ID for automated runs |
| `ASIS_DEFAULT_COMPANY` | Company name for scheduled intelligence runs |
| `ASIS_DEFAULT_SECTOR` | Industry sector for scheduled runs |
| `ASIS_DEFAULT_GEOGRAPHY` | Primary geography for scheduled runs |
| `N8N_WEBHOOK_BASE_URL` | Public n8n webhook base URL for callbacks |
| `SLACK_ASIS_CHANNEL_ID` | Slack channel ID for report delivery |
| `SLACK_APPROVAL_CHANNEL_ID` | Slack channel ID for human approval requests |
| `SENDGRID_FROM_DOMAIN` | SendGrid sender domain |
| `REPORT_EMAIL_RECIPIENT` | Email address for report distribution |
| `TEAMS_WEBHOOK_URL` | Microsoft Teams incoming webhook URL |
| `NOTION_REPORTS_PAGE_ID` | Notion page ID for report archiving |
| `GDRIVE_ASIS_KNOWLEDGE_FOLDER_ID` | Google Drive folder to monitor for knowledge ingestion |
| `LITELLM_PROXY_URL` | LiteLLM proxy URL for embedding calls in WF05 |
| `LITELLM_MASTER_KEY` | LiteLLM master key |
| `QDRANT_URL` | Qdrant server URL |
| `QDRANT_API_KEY` | Qdrant API key |
| `NEWSAPI_KEY` | NewsAPI.org API key for WF07 |
| `COMPETITOR_MONITOR_QUERY` | NewsAPI query string for competitor monitoring |
| `SALESFORCE_INSTANCE_URL` | Salesforce instance URL for WF06 |
| `SALESFORCE_ACCESS_TOKEN` | Salesforce OAuth access token |
| `HUBSPOT_API_URL` | HubSpot API base URL |
| `HUBSPOT_ACCESS_TOKEN` | HubSpot private app access token |

### Credentials

In the n8n UI (`http://localhost:5678`), create the following credentials:

- **Slack ASIS Bot** — Slack API credential with `chat:write`, `channels:read` scopes
- **SendGrid ASIS** — SendGrid API key credential
- **Google Drive ASIS** — OAuth2 credential with Drive read access
- **Notion ASIS** — Notion integration token
- **Redis ASIS** — Redis connection to the shared Redis instance

## Workflows

### WF01 — Scheduled Intelligence Run
Runs every weekday at 07:00. Sends a comprehensive morning intelligence briefing query
to the ASIS webhook for the configured default company and sector.

### WF02 — Enterprise Webhook Trigger
Exposes a POST endpoint (`/webhook/asis-enterprise-trigger`) that external systems
can call to trigger ad-hoc ASIS analyses. Returns `analysis_id` and `stream_url`
immediately (HTTP 202). Validates payload before forwarding to ASIS.

### WF03 — Report Distribution
Listens on the ASIS completion webhook. Routes completed reports to Slack, Email (SendGrid),
Microsoft Teams, or Notion based on the tenant's configured channel preference
(`TENANT_<TENANT_ID>_CHANNEL` environment variable).

### WF04 — Human Approval Gate
Listens on the ASIS completion webhook. If `confidence_score > 8.5` the report is
auto-approved and distributed. If below threshold, it sends a Slack message with
Approve/Reject buttons and waits up to 24 hours for a human decision before timing out.

### WF05 — Qdrant Knowledge Ingestion
Monitors a Google Drive folder for new files. When a file is added, it downloads the
content, chunks it into 1000-character segments with 200-character overlap, embeds
each chunk via LiteLLM, and upserts to the tenant-scoped Qdrant collection.
Supports Google Docs (auto-converted to plain text), PDFs, and plain text files.

### WF06 — CRM Context Enrichment (Sub-workflow)
Called by other workflows when CRM enrichment is needed. Accepts `company_name`,
`crm_record_id`, `crm_type` (salesforce|hubspot), and `tenant_id`. Fetches the
company record from Salesforce or HubSpot and returns a normalised `company_context`
dict ready for use in an ASIS analysis request.

### WF07 — Nightly Competitor Monitor
Runs nightly at 23:00. Fetches the latest 50 news articles from NewsAPI matching the
`COMPETITOR_MONITOR_QUERY`. Each article is scored for strategic relevance (0-10) by
an AI agent. Articles scoring above 7 trigger an ASIS competitor analysis. All scored
articles are cached in Redis with a 7-day TTL to avoid reprocessing.

## Importing Workflows

1. Open n8n at `http://localhost:5678`
2. Go to **Workflows** → **Import from File**
3. Import each JSON file from `asis/n8n/workflows/` in order (01 through 07)
4. Set up credentials as listed above
5. Activate each workflow with the toggle switch

## ASIS Integration

All workflows interact with ASIS via the signed webhook endpoint:

```
POST /v1/webhooks/n8n
Header: X-N8N-Signature: sha256=<hmac_hex>
```

The HMAC signature is computed over the raw JSON body using `ASIS_WEBHOOK_SECRET`.
ASIS verifies this signature and rejects unsigned requests with HTTP 401.

On completion, ASIS POSTs back to the `callback_url` specified in the trigger payload,
which is the n8n completion webhook URL consumed by WF03 and WF04.
