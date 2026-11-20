# KartmaX GA4 Connector

GA4 analytics connector for KartmaX: **MCP-backed** GMV and Sessions by source, **direct GA4** Events (CLI), **REST v1** with JWT, **Google Sheets** export, and an optional **Ops Console** at `/ops`.

**Full map of what we built:** [docs/overview.md](docs/overview.md)

## Features

| Capability | How to use it |
|------------|----------------|
| **REST v1 API** | `POST /api/v1/auth/token` then Bearer JWT on `/api/v1/*` (see table below) |
| **Ops Console** | `ENABLE_OPS_CONSOLE=true` → [http://localhost:8080/ops](http://localhost:8080/ops) |
| **CLI reports** | `py -m src.main report gmv-by-source` (writes JSON under `output/`) |
| **Events by name** | `py -m src.main report events-by-name` — **CLI only** (no v1 REST route) |
| **Docker stack** | Connector + official `analytics-mcp` over HTTP |
| **Legacy channel UI** | `ENABLE_DASHBOARD=true` → `/` (unauthenticated; dev only) |

## Quick start (Docker + Ops Console)

From the repo root on Windows (PowerShell):

```powershell
Copy-Item .env.example .env
# Edit .env: KARTMAX_API_KEY, JWT_SIGNING_SECRET, KARTMAX_OAUTH_CLIENTS,
# GOOGLE_APPLICATION_CREDENTIALS_HOST, service account JSON path, real GA4 property IDs.
# Recommended: ENABLE_DASHBOARD=false, ENABLE_OPS_CONSOLE=true

docker compose up -d --build
Start-Process "http://localhost:8080/ops"
```

In the Ops Console: **Authentication** → enter OAuth client id/secret from `KARTMAX_OAUTH_CLIENTS` → **Report Explorer** or **API Explorer**.

Dev overlay (legacy `/` dashboard + `/ops`):

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

Step-by-step install, env vars, and troubleshooting: [docs/setup-and-run.md](docs/setup-and-run.md)

## REST v1 endpoints

| Method | Path | Notes |
|--------|------|--------|
| `POST` | `/api/v1/auth/token` | `grant_type=client_credentials` |
| `GET` | `/api/v1/health` | Scope `health:read` (JWT) or `X-API-Key` |
| `GET` | `/api/v1/reports/gmv-by-source` | Query: `property_id`, `start_date`, `end_date` |
| `GET` | `/api/v1/reports/sessions-by-source` | Same query params |
| `POST` | `/api/v1/exports/google-sheets` | **JWT only**; body: `property_id`, dates, `spreadsheet_id`, `report_types` |

Production runbook (JWT examples, Sheets, compose): [docs/production.md](docs/production.md)

## CLI (local Python)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt -c constraints.txt
$env:PYTHONPATH = (Get-Location).Path

py -m src.main mcp-status
py -m src.main report gmv-by-source --preset last-7-days
py -m src.main report events-by-name --preset yesterday
```

Optional npm shortcuts (Node not required to run the app): `npm run docker:up`, `npm test` — see [package.json](package.json).

## Tests

```powershell
py -m pip install -r requirements-dev.txt
py -m pytest -q
```

Optional live integration (MCP, real Sheets): set `RUN_GA4_LIVE_TESTS=1` or `RUN_SHEETS_LIVE_TESTS=1` and required env vars (including `GOOGLE_SHEETS_TEST_SPREADSHEET_ID` for Sheets). Details in [docs/production.md](docs/production.md).

## Documentation index

| Doc | Contents |
|-----|----------|
| [docs/overview.md](docs/overview.md) | Architecture, components, runtime profiles |
| [docs/setup-and-run.md](docs/setup-and-run.md) | Windows setup, Docker, Ops Console, CLI, tests |
| [docs/production.md](docs/production.md) | Production deployment, JWT, Sheets export |
| [docs/mcp-http-setup.md](docs/mcp-http-setup.md) | MCP HTTP server on the host |
| [docs/step-3-implementation.md](docs/step-3-implementation.md) | Source report implementation notes |

Configuration template: [.env.example](.env.example) (copy to `.env`; never commit `.env` or service account JSON).