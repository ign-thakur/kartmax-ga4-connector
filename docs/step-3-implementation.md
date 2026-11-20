# Step 3 — MCP report migration (GMV & Sessions by **source**)

This document is the **authoritative Step 3 spec**, including the business correction to use **`sessionSource`** (traffic source / platform) instead of **`sessionDefaultChannelGroup`** (aggregated channel groups).

Steps 1–2 are complete (MCP HTTP client + service-account Bearer forwarding). **Do not start coding Step 3 until this spec is approved.**

---

## Business requirement

KartmaX needs **revenue and sessions by individual traffic source/platform** (e.g. `google`, `facebook.com`, `m.facebook.com`, `bing`, `GH_Meta`, WhatsApp campaign URLs, etc.).

We **do not** want rolled-up channel groups such as Organic Search, Paid Search, Organic Social, or Paid Social.

---

## Report definitions (target)

Both reports use **dynamic `start_date` / `end_date`**, **daily granularity**, and **MCP `run_report`** as the data-access path (Steps 1–2).

### 1. GMV by source

| Field | Value |
|--------|--------|
| Dimensions | `date`, `sessionSource` |
| Metric | `grossPurchaseRevenue` |
| Row shape | `{ "date": "YYYY-MM-DD", "source": "<GA4 raw>", "gmv": "<string numeric>" }` |
| JSON `report_type` | `gmv_by_source` (see naming migration below) |

### 2. Sessions by source

| Field | Value |
|--------|--------|
| Dimensions | `date`, `sessionSource` |
| Metric | `sessions` |
| Row shape | `{ "date": "YYYY-MM-DD", "source": "<GA4 raw>", "sessions": "<string numeric>" }` |
| JSON `report_type` | `sessions_by_source` |

### Implementation rules

1. Replace **`sessionDefaultChannelGroup`** with **`sessionSource`** in both report definitions (MCP arguments and any direct-API fallback used in tests).
2. **Preserve raw** `sessionSource` from GA4 (case, punctuation, `(direct)`, `(not set)`). **No allowlist** of Google/Facebook/etc.
3. Support **all** sources GA4 returns (up to API row limits; paginate if needed later).
4. Normalize only empty/null source to a single sentinel, e.g. `"(not set)"` (same pattern as today’s channel parser).
5. Keep existing payload metadata: `property_id`, `report_type`, `start_date`, `end_date`, `generated_at`, `currency` (GMV), `data[]`.
6. **Dynamic dates** via existing `resolve_date_range` / ISO query params (unchanged).
7. **Validate** that live responses contain plausible `sessionSource` values for the configured `GA4_PROPERTY_ID` (smoke / integration test against property, not a fixed enum).
8. **Out of scope for Step 3:** Events report, dashboard UI/API, KartmaX backend REST v1 (unless explicitly re-added).

---

## GA4 Data API compatibility check (pre-implementation)

**Question:** Can `sessionSource` be queried with `grossPurchaseRevenue` and `sessions`?

### Official schema

- `sessionSource` — session-scoped: *“The source that initiated a session.”* ([API schema](https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema))
- `grossPurchaseRevenue` — purchase revenue from `purchase` and related commerce events.

GA4 documents **dimension–metric compatibility** rules; some session dimensions cannot be combined with hit-scoped metrics. Third-party guides often warn about `sessionSource` + event-scoped metrics, so **compatibility must be verified per property**.

### Live verification (this repo, property `GA4_PROPERTY_ID` from `.env`)

Direct `run_report` against the Data API (same credentials as today):

| Query | Result |
|--------|--------|
| `date` + `sessionSource` + `grossPurchaseRevenue` (yesterday) | **OK** — rows returned; example: `20261118`, `google`, `80655.000222` |
| `date` + `sessionSource` + `sessions` (yesterday) | **OK** — example: `20261118`, `google`, `4094` |

Seven-day sample: **65 distinct** `sessionSource` values in one property (e.g. `google`, `GH_Meta`, `(direct)`, `facebook.com`, `bing`, `m.facebook.com`, …), confirming **non–channel-group** granularity.

**Conclusion for Step 3:** `sessionSource` + `grossPurchaseRevenue` and `sessionSource` + `sessions` are **compatible for our configured property**. Re-run the same probe after schema/Google updates or when changing properties.

### Attribution and interpretation limitations (product / analytics)

These are **not** API blockers but affect how KartmaX interprets “by source”:

| Topic | Limitation |
|--------|------------|
| **Attribution** | `sessionSource` is **session**-based (last/non-direct session rules per GA4), not necessarily last-click on purchase. Revenue is attributed to the **session’s** source for that day/row. |
| **Naming** | Sources are **UTM/tagging-derived strings** (`google`, `facebook.com`, custom campaign names). They are not normalized brand names unless you tag them that way. |
| **Paid vs organic** | Same hostname can appear under multiple sources; use `sessionMedium` / `sessionCampaignName` in a future report if you need split paid/organic **without** channel groups. |
| **`(direct)` / `(not set)`** | GA4 reserved values; preserve as returned. |
| **WhatsApp / apps** | Appear only if UTM or referrer resolves to a distinct `sessionSource` string. |
| **Cross-day purchases** | Daily `date` dimension + session source counts revenue on the **event date**, not the session start date, per GA4’s standard reporting behavior for this query shape. |
| **Row volume** | High cardinality sources × days can hit **250k row** limits; plan pagination (`limit`/`offset`) if exports grow. |

---

## Step 3 scope (unchanged from original plan, except source semantics)

### In scope

1. **MCP data layer** — GMV and Sessions fetches call MCP `run_report` with Bearer auth (Step 2).
2. **Provider abstraction** — e.g. `src/clients/ga4_provider.py` or `src/mcp/run_report_adapter.py` mapping MCP JSON → existing row validators where possible.
3. **Report modules** — update fetch logic dimensions/metrics/row keys; keep CLI command names or add aliases (see migration).
4. **Parsers & validators** — rename `channel` → `source` in row dicts; update `validate_report_rows` field checks.
5. **Tests** — unit tests for parsing/validation; integration test with mocked MCP; optional live property smoke (gated by env).
6. **JSON exports** — still written under `output/` with same metadata pattern.

### Out of scope

- Events report (`events_by_name`) — stays on **direct** Data API.
- Dashboard (`src/dashboard/*`, static UI) — still reads old `channel` shape until a later step.
- MCP OAuth, new REST endpoints for KartmaX Backend (unless separately requested).

---

## Proposed file-level changes (Step 3)

| Action | File | Notes |
|--------|------|--------|
| **Modify** | `src/clients/analytics_client.py` | `SOURCE_DIMENSION = "sessionSource"`; `run_source_report()`; `parse_source_metric_rows()` → `{date, source, …}` |
| **Modify** | `src/reports/gmv_by_channel.py` | MCP-backed fetch; dimensions `date` + `sessionSource`; `gmv`; consider rename to `gmv_by_source.py` |
| **Modify** | `src/reports/sessions_by_channel.py` | Same for sessions |
| **Modify** | `src/reports/output.py` | Validate `source` not `channel` |
| **Modify** | `src/cli/commands.py` | Docstrings + optional aliases `gmv-by-source` / `sessions-by-source` |
| **New** | `src/mcp/run_report_adapter.py` | Build MCP `run_report` args; map response → rows + `currency` |
| **New** | `src/mcp/report_queries.py` | Shared dimension/metric constants for two reports |
| **Modify** | `tests/test_report_output.py` | `source` rows, `sessionSource` fixtures |
| **Modify** | `tests/test_dashboard_repository.py` | **Only if** still using channel fixtures; or skip until dashboard migration |
| **New** | `tests/test_mcp_report_adapter.py` | MCP JSON → row normalization |
| **New** | `tests/test_ga4_source_compatibility.py` | Optional live test, `@pytest.mark.integration` |

**Report type / filename migration (recommendation):**

- `report_type`: `gmv_by_source` / `sessions_by_source`
- File stems: `gmv_by_source_YYYYMMDD.json`, `sessions_by_source_YYYYMMDD.json`
- Keep **CLI** `report gmv-by-channel` as deprecated alias for one release if needed, or break and document in changelog.

---

## MCP `run_report` argument template

```json
{
  "property_id": "<GA4_PROPERTY_ID>",
  "date_ranges": [{"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}],
  "dimensions": ["date", "sessionSource"],
  "metrics": ["grossPurchaseRevenue"],
  "limit": 100000
}
```

Sessions report: same with `"metrics": ["sessions"]`.

Authenticated HTTP: all tool calls use **service-account Bearer** (Step 2).

---

## Acceptance criteria

1. CLI (or MCP-backed internal API used by CLI) returns daily rows with **raw** `source` values for the requested date range.
2. No hardcoded source list; property returns **≥1** row for a known range in integration/smoke tests.
3. GMV rows include `currency` when MCP/GA4 metadata provides it.
4. All unit tests pass; live smoke on property confirms `sessionSource` + both metrics.
5. Events report and dashboard behavior **unchanged**.

---

## Pre-flight checklist before coding

- [ ] Product accepts **session attribution** semantics (see limitations table).
- [ ] Confirm filename / `report_type` rename with KartmaX Backend consumers.
- [ ] MCP server running HTTP + connector `MCP_SERVER_URL` + `GOOGLE_APPLICATION_CREDENTIALS`.
- [ ] Re-run compatibility probe when `GA4_PROPERTY_ID` changes.