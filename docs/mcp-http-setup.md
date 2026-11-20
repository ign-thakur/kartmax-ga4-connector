# Google Analytics MCP — HTTP setup

KartmaX runs [Google’s official `analytics-mcp`](https://github.com/googleanalytics/google-analytics-mcp) as a **separate process**. This connector talks to it over **Streamable HTTP** using the [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).

## Start the MCP server (HTTP)

Prerequisites:

- Python 3.10+
- [pipx](https://pipx.pypa.io/) (recommended) or a venv with `analytics-mcp` installed
- Google Cloud: **Analytics Data API** and **Analytics Admin API** enabled

### Install and run

```powershell
pipx install analytics-mcp
```

Set credentials on the **MCP server process** only if you use stdio mode. For HTTP, see [Authentication](#authentication) below.

```powershell
# Stateless HTTP (recommended for local dev; matches Cloud Run style)
pipx run analytics-mcp --transport http --stateless-http --host 127.0.0.1 --port 8000
```

The server prints a URL like `http://127.0.0.1:8000/mcp`. Use that full path in the connector.

### Optional: OAuth on the MCP server

Only needed for multi-tenant, per-user sign-in (`--oauth` with `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET`). KartmaX has **not** enabled this without explicit approval.

## Configure the connector

Add to `.env` (see `.env.example`):

```env
MCP_SERVER_URL=http://127.0.0.1:8000/mcp
MCP_TIMEOUT=30
```

Check connectivity:

```powershell
py -m src.main mcp-status
```

## Authentication

### What the official server does in HTTP mode

In `analytics_mcp/server.py`, **HTTP transport always** builds the app with `require_request_credentials=True`:

- The MCP server does **not** use server-side `GOOGLE_APPLICATION_CREDENTIALS` / ADC for tool calls in this mode.
- **`run_report` and other tools** require an `Authorization: Bearer <google_oauth_access_token>` header on each MCP HTTP request (unless using the built-in MCP OAuth server with `--oauth`).

`list_tools` (used by `mcp-status`) typically works **without** a Bearer token when `--oauth` is not enabled.

### KartmaX service account (today)

The connector still uses a **service account JSON** for **direct** GA4 access (Events report and existing CLI). That file is **not** automatically consumed by `analytics-mcp` in HTTP mode.

**Implemented (Step 2):**

1. The connector loads the same service account JSON as direct GA4 (`GOOGLE_APPLICATION_CREDENTIALS`).
2. It mints and caches access tokens with scope `https://www.googleapis.com/auth/analytics.readonly`, refreshing only when expired.
3. Authenticated MCP calls send `Authorization: Bearer <access_token>` on every HTTP request (via a shared `httpx` client).

That is **not** interactive user OAuth and does **not** enable MCP `--oauth`.

Verify end-to-end:

```powershell
py -m src.main mcp-run-report-smoke
```

### Alternatives (require explicit approval)

| Approach | Notes |
|----------|--------|
| MCP **stdio** + local ADC on server | Service account via `GOOGLE_APPLICATION_CREDENTIALS` on the MCP process; not HTTP between apps |
| MCP HTTP + **`--oauth`** | Built-in MCP OAuth 2.1; user sign-in, not service account |
| **ADC on MCP host** only in **stdio** mode | Documented upstream default for desktop assistants |

## Environment reference

| Variable | Required | Description |
|----------|----------|-------------|
| `MCP_SERVER_URL` | Yes (for MCP commands) | Streamable HTTP endpoint, e.g. `http://127.0.0.1:8000/mcp` |
| `MCP_TIMEOUT` | No | Connect/write/pool timeout in seconds (default `30`; read timeout stays ≥ 300s for large reports) |

Do not put secrets in `MCP_SERVER_URL` (no `user:pass@` in URLs).