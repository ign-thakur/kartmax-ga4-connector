# Production deployment (Docker)

This guide covers running the **KartmaX GA4 Connector** with the official **Google Analytics MCP** HTTP server in containers. Secrets stay on the host and are injected at runtime — they are never copied into images.

## Architecture

| Service | Image | Role |
|---------|-------|------|
| `ga4-connector` | `kartmax/ga4-connector` | FastAPI: `/api/v1/*` (always); ops console when `ENABLE_OPS_CONSOLE=true`; legacy dashboard when `ENABLE_DASHBOARD=true` |
| `analytics-mcp` | `kartmax/analytics-mcp:1.1.0` | Official `analytics-mcp` with `--transport http --stateless-http` |

Inside Docker, the connector calls MCP at `http://analytics-mcp:8080/mcp` (not `localhost`).

## Prerequisites

- Docker Engine 24+ and Docker Compose v2
- Google Cloud service account JSON with **Analytics Data API** and **Google Sheets API** enabled
- Target spreadsheets shared with the service account email (**Editor**)
- A strong `JWT_SIGNING_SECRET` (≥32 chars) and `KARTMAX_OAUTH_CLIENTS` JSON for KartmaX Backend (**recommended**)
- Or `KARTMAX_API_KEY` for legacy `X-API-Key` callers (temporary)

## Configuration

1. Copy `.env.example` to `.env` and set:

| Variable | Required | Description |
|----------|----------|-------------|
| `JWT_SIGNING_SECRET` | Recommended | HMAC secret for signing backend JWTs (≥32 chars) |
| `KARTMAX_OAUTH_CLIENTS` | Recommended | JSON array: `client_id`, `client_secret`, `property_ids`, optional `scopes` |
| `JWT_ISSUER` | Optional | Token issuer (default `kartmax-ga4-connector`) |
| `JWT_AUDIENCE` | Optional | Token audience (default `kartmax-backend`) |
| `JWT_ACCESS_TOKEN_TTL_SECONDS` | Optional | Access token TTL (default `1800` = 30 minutes) |
| `KARTMAX_API_KEY` | Legacy | `X-API-Key` header (backward compatible; no property allowlist) |
| `GOOGLE_APPLICATION_CREDENTIALS_HOST` | Yes | Host path to SA JSON (mounted read-only into connector) |
| `GA4_PROPERTY_ID` | Optional | Default property for CLI; APIs use `property_id` query param |
| `GA4_REPORTING_TIMEZONE` | Optional | Reporting TZ label (default `UTC` in compose) |
| `MCP_TIMEOUT` | Optional | MCP HTTP timeout seconds (default `30`) |
| `REPORT_MAX_RANGE_DAYS` | Optional | Max inclusive date span (default `366`) |
| `ENABLE_DASHBOARD` | Optional | `false` = hide legacy unauthenticated UI (recommended prod) |
| `ENABLE_OPS_CONSOLE` | Optional | `true` = serve JWT ops console at `/ops` (uses `/api/v1` only) |
| `CONNECTOR_HOST_PORT` | Optional | Host port mapped to connector `8080` (default `8080`) |

2. Place the service account file at the path referenced by `GOOGLE_APPLICATION_CREDENTIALS_HOST` (for example `.secrets/service-account.json`).

**Production profile (recommended):** `ENABLE_DASHBOARD=false`, `ENABLE_OPS_CONSOLE=true` — `/api/v1/*` plus the ops console at `/ops`. The console HTML is public, but data requires a JWT from `POST /api/v1/auth/token` (secrets are not stored in the browser). Legacy unauthenticated routes (`/`, `/api/dashboard`, `/api/events`) return 404.

**API-only (no UI):** set both `ENABLE_DASHBOARD=false` and `ENABLE_OPS_CONSOLE=false`.

**Development profile:** run with the dev overlay:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

## Build and start

From the repository root:

```bash
docker compose build
docker compose up -d
```

Build both images:

- `Dockerfile` — connector
- `docker/Dockerfile.mcp` — `analytics-mcp==1.1.0`

Dependency versions are pinned in `requirements.txt` and `constraints.txt`.

## KartmaX Backend authentication (JWT)

**Obtain access token (client credentials):**

```bash
curl -sS -X POST http://localhost:8080/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=kartmax-backend" \
  -d "client_secret=$KARTMAX_CLIENT_SECRET"
```

Response:

```json
{
  "access_token": "<jwt>",
  "token_type": "Bearer",
  "expires_in": 1800,
  "scope": "health:read reports:gmv reports:sessions"
}
```

Use `Authorization: Bearer <jwt>` on `/api/v1/*`. Tokens are short-lived (30 minutes); request a new token with client credentials when expired. **No refresh tokens.**

JWT claims include `client_id`, `scope`, and `properties` (allowlisted GA4 property IDs). Report APIs reject requests when `property_id` is not in the token.

| Scope | Endpoints |
|-------|-----------|
| `health:read` | `GET /api/v1/health` |
| `reports:gmv` | `GET /api/v1/reports/gmv-by-source` |
| `reports:sessions` | `GET /api/v1/reports/sessions-by-source` |

Legacy `X-API-Key` remains supported temporarily on report/health routes. Bearer is recommended for new integrations.

## Google Sheets export

**Prerequisites**

1. Enable **Google Sheets API** in the same GCP project as the service account.
2. Share the spreadsheet with the service account email as **Editor**.
3. Keep existing tabs **`GMV by Source`** and **`Sessions by Source`** with the expected header row (tabs are **not** auto-created).

**Export (Bearer JWT required):**

```bash
curl -sS -X POST http://localhost:8080/api/v1/exports/google-sheets \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "352673114",
    "report_types": ["gmv_by_source", "sessions_by_source"],
    "start_date": "2026-11-18",
    "end_date": "2026-11-18",
    "spreadsheet_id": "1Cr-Rt0LtjqguWTrGuxTxMfSSBQfjO--X6U12bIXzdeg"
  }'
```

**Response (example):**

```json
{
  "success": true,
  "spreadsheet_id": "1Cr-Rt0LtjqguWTrGuxTxMfSSBQfjO--X6U12bIXzdeg",
  "spreadsheet_url": "https://docs.google.com/spreadsheets/d/.../edit",
  "property_id": "352673114",
  "start_date": "2026-11-18",
  "end_date": "2026-11-18",
  "synced_at": "2026-11-19T10:15:00+00:00",
  "reports": [
    {
      "report_type": "gmv_by_source",
      "tab": "GMV by Source",
      "rows_exported": 5,
      "rows_updated": 2,
      "rows_inserted": 3,
      "rows_total": 120
    }
  ]
}
```

Rows are **upserted** by `Date` + `Property ID` + `Source`. Raw `sessionSource` values and numeric metrics are preserved. `Last Synced At` is UTC.

| HTTP | Meaning |
|------|---------|
| 401 | Missing/invalid Bearer token (export does not accept `X-API-Key`) |
| 403 | JWT property allowlist or Sheets permission denied |
| 404 | Spreadsheet ID not found |
| 422 | Missing tab, header mismatch, or invalid request body |

Live integration test: `RUN_SHEETS_LIVE_TESTS=1 py -m pytest tests/test_sheets_export_live.py -q`

Google **service account** credentials (for MCP/GA4) are separate and never returned to KartmaX Backend.

## Health checks

**Connector (authenticated):**

```bash
curl -sS -H "Authorization: Bearer $ACCESS_TOKEN" http://localhost:8080/api/v1/health
```

Expected shape:

```json
{
  "status": "ok",
  "connector": "ok",
  "mcp": {
    "connected": true,
    "run_report_available": true,
    "error_message": null
  }
}
```

The MCP server URL is **not** included in the public health response.

**MCP process:** compose healthcheck opens TCP to `127.0.0.1:8080` inside the `analytics-mcp` container.

## API smoke tests

GMV by source:

```bash
curl -sS -H "Authorization: Bearer $ACCESS_TOKEN" \
  "http://localhost:8080/api/v1/reports/gmv-by-source?property_id=YOUR_PROPERTY&start_date=2026-11-01&end_date=2026-11-07"
```

Sessions by source:

```bash
curl -sS -H "Authorization: Bearer $ACCESS_TOKEN" \
  "http://localhost:8080/api/v1/reports/sessions-by-source?property_id=YOUR_PROPERTY&start_date=2026-11-01&end_date=2026-11-07"
```

Missing or invalid Bearer token should return **401**. Wrong GA4 `property_id` for the client returns **403**.

## Troubleshooting

| Symptom | Likely cause | Action |
|---------|----------------|--------|
| Health `mcp.connected: false` | MCP not reachable | `docker compose logs analytics-mcp`; confirm `MCP_SERVER_URL` is `http://analytics-mcp:8080/mcp` in connector env |
| `502` / token errors on reports | Invalid or unreadable SA JSON | Verify mount path and file permissions; check `GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/google-service-account.json` in container |
| `503` MCP errors | MCP HTTP down or timeout | Increase `MCP_TIMEOUT`; restart `analytics-mcp` |
| `401` on all v1 routes | Wrong or missing `KARTMAX_API_KEY` | Align header `X-API-Key` with `.env` |
| `404` on `/` in prod | Expected when `ENABLE_DASHBOARD=false` | Use dev compose overlay or set `ENABLE_DASHBOARD=true` locally |
| Property has no data | GA4 permissions or date range | Confirm SA has Viewer on the property; try a narrower date range |

**Logs:**

```bash
docker compose logs -f ga4-connector
docker compose logs -f analytics-mcp
```

**Local pytest (no Docker):**

```bash
pip install -r requirements-dev.txt -c constraints.txt
py -m pytest -q
```

## Security notes

- Do not commit `.env`, service account JSON, or real API keys.
- `.dockerignore` excludes `.secrets/`, `.env`, and credential filenames from build context.
- P1 items (property allowlists, rate limiting, timing-safe key compare) are out of scope for this hardening PR.