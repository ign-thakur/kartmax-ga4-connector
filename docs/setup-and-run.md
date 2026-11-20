# Setup and run (Windows PowerShell)

This guide lists **exact commands** to install, configure, and run the **KartmaX GA4 Connector** and its **Ops Console** on Windows. Commands assume you are in the repository root unless noted.

Related docs:

- [Project overview (what we built)](overview.md)
- [Production deployment (Docker)](production.md)
- [MCP HTTP setup](mcp-http-setup.md)

---

## 1. Prerequisites

| Requirement | Purpose | Notes |
|-------------|---------|--------|
| **Python 3.12+** (3.10+ minimum) | CLI, local API, tests | Install from [python.org](https://www.python.org/downloads/). Verify: `py --version` |
| **Docker Desktop** | Recommended full stack (connector + `analytics-mcp`) | Docker Compose v2 included |
| **Git** | Clone the repository | Optional if you already have the folder |
| **Node.js** | **Not required** | Optional only if you want `npm run …` shortcuts from `package.json` (no frontend build) |

The Ops Console is **static** assets under `src/ops_console/static/` — served by FastAPI when `ENABLE_OPS_CONSOLE=true`. No React, Vite, or `npm install` for the UI.

---

## 2. Repository setup

```powershell
# Example clone (adjust URL/path to your remote)
git clone <YOUR_REPO_URL> kartmax-ga4-connector
Set-Location kartmax-ga4-connector
```

If you already have the project:

```powershell
Set-Location C:\Users\Admin\Desktop\KartmaX\kartmax-ga4-connector
```

---

## 3. Python virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If script execution is blocked:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

---

## 4. Python dependencies

**Runtime + CLI:**

```powershell
py -m pip install --upgrade pip
py -m pip install -r requirements.txt -c constraints.txt
```

**Development (pytest):**

```powershell
py -m pip install -r requirements-dev.txt
```

For local imports and CLI, set the module path for the session:

```powershell
$env:PYTHONPATH = (Get-Location).Path
```

---

## 5. Environment variables

Copy the example file and edit values (never commit `.env`):

```powershell
Copy-Item .env.example .env
notepad .env
```

Minimum fields to review:

| Variable | Description |
|----------|-------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to SA JSON when running Python on the **host** (e.g. `.secrets/service-account.json`) |
| `GOOGLE_APPLICATION_CREDENTIALS_HOST` | Host path mounted into Docker (same file; used by `docker-compose.yml`) |
| `GA4_PROPERTY_ID` | Your GA4 property numeric ID |
| `GA4_REPORTING_TIMEZONE` | Property reporting time zone |
| `MCP_SERVER_URL` | `http://127.0.0.1:8000/mcp` on host; overridden in Docker to `http://analytics-mcp:8080/mcp` |
| `KARTMAX_API_KEY` | Legacy API key (**required** by Compose even if you use JWT) |
| `JWT_SIGNING_SECRET` | ≥32 random characters |
| `KARTMAX_OAUTH_CLIENTS` | JSON array of OAuth clients (see below) |
| `ENABLE_DASHBOARD` | `true` = legacy unauthenticated UI at `/` (dev only) |
| `ENABLE_OPS_CONSOLE` | `true` = Ops Console at `/ops` |
| `CONNECTOR_HOST_PORT` | Host port for connector (default `8080`) |

`.env` is loaded automatically by the connector when settings modules import (project root `.env`).

---

## 6. Google Service Account setup

1. In Google Cloud: enable **Google Analytics Data API**, **Google Analytics Admin API**, and **Google Sheets API** (for Sheets export).
2. Create a service account and download a JSON key.
3. Store the key **outside git** (gitignore covers `*service-account*.json` and `.secrets/`):

```powershell
New-Item -ItemType Directory -Force -Path .secrets
# Copy your downloaded key to:
# .secrets\service-account.json
```

4. In GA4 Admin, grant the service account email **Viewer** (or sufficient read access) on the property.
5. For Sheets export: share each target spreadsheet with the service account email as **Editor**.

In `.env`:

```env
GOOGLE_APPLICATION_CREDENTIALS=.secrets/service-account.json
GOOGLE_APPLICATION_CREDENTIALS_HOST=.secrets/service-account.json
GA4_PROPERTY_ID=<YOUR_GA4_PROPERTY_ID>
```

---

## 7. JWT configuration

Generate a strong signing secret (example — replace with your own):

```powershell
# 48 random bytes, base64 (store in .env as JWT_SIGNING_SECRET)
[Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }) -as [byte[]])
```

Set in `.env`:

```env
JWT_SIGNING_SECRET=<YOUR_JWT_SIGNING_SECRET>
JWT_ISSUER=kartmax-ga4-connector
JWT_AUDIENCE=kartmax-backend
JWT_ACCESS_TOKEN_TTL_SECONDS=1800
KARTMAX_API_KEY=<YOUR_LONG_RANDOM_API_KEY>
KARTMAX_OAUTH_CLIENTS=[{"client_id":"kartmax-backend","client_secret":"<YOUR_CLIENT_SECRET>","property_ids":["<YOUR_GA4_PROPERTY_ID>"],"scopes":["reports:gmv","reports:sessions","health:read"]}]
```

Scopes used by the Ops Console:

- `health:read` — Overview health check
- `reports:gmv` — GMV report + GMV Sheets export
- `reports:sessions` — Sessions report + Sessions Sheets export

Sheets export also requires a valid Bearer JWT with the matching scopes (no legacy `X-API-Key` on that route).

---

## 8. MCP server setup

### Option A — Docker Compose (recommended)

MCP runs as service `analytics-mcp` (see `docker/Dockerfile.mcp`, image `kartmax/analytics-mcp:1.1.0`). No separate MCP install on the host.

### Option B — MCP on the host (Python dev without Docker for MCP)

Install and run the official server (see [mcp-http-setup.md](mcp-http-setup.md)):

```powershell
pipx install analytics-mcp
pipx run analytics-mcp --transport http --stateless-http --host 127.0.0.1 --port 8000
```

In `.env` on the host:

```env
MCP_SERVER_URL=http://127.0.0.1:8000/mcp
```

Verify from the connector repo (with venv active and `.env` set):

```powershell
$env:PYTHONPATH = (Get-Location).Path
py -m src.main mcp-status
py -m src.main mcp-run-report-smoke
```

---

## 9. Docker image build

From the repository root:

```powershell
docker compose build
```

Builds:

- `kartmax/ga4-connector:latest` — `Dockerfile`
- `kartmax/analytics-mcp:1.1.0` — `docker/Dockerfile.mcp`

---

## 10. Docker Compose startup

### Initial start (production-style API + optional flags from `.env`)

Ensure `.env` includes at least `KARTMAX_API_KEY` and `GOOGLE_APPLICATION_CREDENTIALS_HOST` pointing to an existing file.

**Recommended for Ops Console without legacy dashboard:**

In `.env`:

```env
ENABLE_DASHBOARD=false
ENABLE_OPS_CONSOLE=true
```

Start:

```powershell
docker compose up -d
```

### Development overlay (legacy dashboard + Ops Console)

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

This sets `ENABLE_DASHBOARD=true` and `ENABLE_OPS_CONSOLE=true` on the connector service.

### Optional npm shortcuts (Node not required)

If Node.js is installed:

```powershell
npm run docker:build
npm run docker:up
npm run docker:up:dev
```

---

## 11. Enabling the Ops Console

| Mode | Configuration |
|------|----------------|
| **Docker** | `ENABLE_OPS_CONSOLE=true` in `.env`, or use `docker-compose.dev.yml` |
| **Local uvicorn** | Set env vars then run uvicorn (see below) |

Docker reads `ENABLE_OPS_CONSOLE` from `.env` via `docker-compose.yml`.

Local run with Ops Console:

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = (Get-Location).Path
$env:ENABLE_OPS_CONSOLE = "true"
$env:ENABLE_DASHBOARD = "false"
py -m uvicorn src.dashboard.app:app --host 127.0.0.1 --port 8080
```

When `ENABLE_OPS_CONSOLE=false`, `GET /ops` returns **404**.

---

## 12. Accessing the frontend

Connector URL (default host port from `CONNECTOR_HOST_PORT`, usually **8080**):

| URL | When available |
|-----|----------------|
| **http://localhost:8080/ops** | `ENABLE_OPS_CONSOLE=true` |
| http://localhost:8080/ | Legacy dashboard only if `ENABLE_DASHBOARD=true` |
| http://localhost:8080/api/v1/… | Always (when server is running) |

**Ops Console workflow:**

1. Open **http://localhost:8080/ops**
2. Go to **Authentication** → enter `client_id` and `client_secret` from `KARTMAX_OAUTH_CLIENTS` → **Generate token** (stored in memory only in the browser).
3. Use **Overview**, **Report Explorer**, **API Explorer**, and **Google Sheets** sections.

---

## 13. CLI commands

With venv active and `PYTHONPATH` set to the repo root:

```powershell
$env:PYTHONPATH = (Get-Location).Path

# Connectivity
py -m src.main status
py -m src.main mcp-status
py -m src.main mcp-run-report-smoke

# Reports (write JSON under output/)
py -m src.main report gmv-by-source --preset last-7-days
py -m src.main report sessions-by-source --preset last-7-days
py -m src.main report events-by-name --preset last-7-days

# Local web server (respects ENABLE_DASHBOARD / ENABLE_OPS_CONSOLE from .env)
py -m src.main serve --host 127.0.0.1 --port 8080
```

Help:

```powershell
py -m src.main --help
py -m src.main report --help
```

---

## 14. Automated tests

```powershell
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements-dev.txt
$env:PYTHONPATH = (Get-Location).Path
py -m pytest -q
```

Or with npm (optional):

```powershell
npm test
```

Optional live tests (require real credentials and env):

```powershell
$env:RUN_GA4_LIVE_TESTS = "1"
py -m pytest tests/test_ga4_mcp_parity.py -q

$env:RUN_SHEETS_LIVE_TESTS = "1"
py -m pytest tests/test_sheets_export_live.py -q
```

---

## 15. Stopping and restarting

**Stop containers (keep images/volumes):**

```powershell
docker compose down
```

**Restart after `.env` changes:**

```powershell
docker compose down
docker compose up -d
```

**Restart one service:**

```powershell
docker compose restart ga4-connector
docker compose restart analytics-mcp
```

---

## 16. Command cheat sheet (PowerShell)

### Initial setup (once)

```powershell
Set-Location C:\Users\Admin\Desktop\KartmaX\kartmax-ga4-connector
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -r requirements.txt -c constraints.txt
py -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
# Place SA JSON at .secrets\service-account.json and edit .env
```

### Normal startup (Docker + Ops Console)

```powershell
Set-Location C:\Users\Admin\Desktop\KartmaX\kartmax-ga4-connector
# .env: ENABLE_OPS_CONSOLE=true, ENABLE_DASHBOARD=false, secrets filled in
docker compose up -d
Start-Process "http://localhost:8080/ops"
```

### Rebuild after code changes

```powershell
docker compose up -d --build
```

Full no-cache rebuild:

```powershell
docker compose build --no-cache
docker compose up -d
```

### View logs

```powershell
docker compose logs -f --tail=100
docker compose logs -f ga4-connector
docker compose logs -f analytics-mcp
```

### Check container health

```powershell
docker compose ps
```

`analytics-mcp` defines a Compose healthcheck. The connector has no Compose healthcheck; use the API or Ops Console:

```powershell
# Expect 401 without auth — proves the API is listening
Invoke-WebRequest -Uri "http://localhost:8080/api/v1/health" -UseBasicParsing
```

With a valid JWT (replace `<ACCESS_TOKEN>`):

```powershell
Invoke-WebRequest -Uri "http://localhost:8080/api/v1/health" -Headers @{ Authorization = "Bearer <ACCESS_TOKEN>" } -UseBasicParsing
```

Obtain a token (replace placeholders):

```powershell
$body = @{
  grant_type     = "client_credentials"
  client_id      = "<YOUR_CLIENT_ID>"
  client_secret  = "<YOUR_CLIENT_SECRET>"
}
Invoke-RestMethod -Method Post -Uri "http://localhost:8080/api/v1/auth/token" -ContentType "application/x-www-form-urlencoded" -Body $body
```

### Run tests

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = (Get-Location).Path
py -m pytest -q
```

### Stop the application

```powershell
docker compose down
```

---

## 17. Common errors and troubleshooting

| Symptom | Likely cause | What to do |
|---------|----------------|------------|
| `Python was not found` | Python not on PATH | Use `py` launcher or install Python 3.12+ |
| `Set KARTMAX_API_KEY in .env` on `docker compose up` | Missing required Compose var | Set `KARTMAX_API_KEY` in `.env` |
| `GOOGLE_APPLICATION_CREDENTIALS_HOST` error | SA path invalid | Ensure file exists; use forward slashes or escaped backslashes in `.env` |
| `GET /ops` → 404 | Ops Console disabled | Set `ENABLE_OPS_CONSOLE=true` and recreate/restart `ga4-connector` |
| Health → 401 in Ops Console | No or expired JWT | Generate token in **Authentication**; check scopes include `health:read` |
| Reports → 403 | Property not in JWT allowlist | Add `property_id` to client's `property_ids` in `KARTMAX_OAUTH_CLIENTS` |
| MCP degraded / `run_report` unavailable | `analytics-mcp` down or unreachable | `docker compose ps`; `docker compose logs analytics-mcp`; on host dev, check `MCP_SERVER_URL` |
| `mcp-status` fails on host | MCP not running | Start MCP (Option B) or use Docker stack |
| Sheets export fails | Sheets API off or no share | Enable API; share spreadsheet with SA email as Editor |
| `Invalid client credentials` | Wrong id/secret or JSON typo | Fix `KARTMAX_OAUTH_CLIENTS`; restart container after `.env` change |
| Port 8080 in use | Another process | Change `CONNECTOR_HOST_PORT` in `.env` and `docker compose up -d` |

For deeper production notes (JWT examples, Sheets API), see [production.md](production.md).