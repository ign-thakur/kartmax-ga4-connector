/**
 * KartmaX GA4 Ops Console — in-memory JWT only; no localStorage for secrets or tokens.
 */
(function () {
  "use strict";

  const API = "/api/v1";

  const session = {
    accessToken: null,
    expiresAt: null,
    tokenType: "Bearer",
    expiresIn: null,
    scope: "",
    properties: [],
    issuedAt: null,
  };

  let countdownTimer = null;
  const tableState = {
    gmv: { groups: [], currency: "" },
    sessions: { groups: [] },
  };

  const ENDPOINTS = [
    {
      id: "health",
      method: "GET",
      path: `${API}/health`,
      title: "Health",
      description: "Connector and MCP connectivity status.",
      headers: ["Authorization: Bearer &lt;access_token&gt; (scope health:read)"],
      query: [],
      body: null,
      needsAuth: true,
    },
    {
      id: "token",
      method: "POST",
      path: `${API}/auth/token`,
      title: "OAuth token",
      description: "Client credentials grant.",
      headers: ["Content-Type: application/x-www-form-urlencoded"],
      query: [],
      body: "grant_type=client_credentials&client_id=…&client_secret=…",
      needsAuth: false,
      form: true,
    },
    {
      id: "gmv",
      method: "GET",
      path: `${API}/reports/gmv-by-source`,
      title: "GMV by Source",
      description: "GMV aggregated by session source.",
      headers: ["Authorization: Bearer &lt;access_token&gt; (scope reports:gmv)"],
      query: ["property_id", "start_date", "end_date"],
      body: null,
      needsAuth: true,
    },
    {
      id: "sessions",
      method: "GET",
      path: `${API}/reports/sessions-by-source`,
      title: "Sessions by Source",
      description: "Sessions aggregated by session source.",
      headers: ["Authorization: Bearer &lt;access_token&gt; (scope reports:sessions)"],
      query: ["property_id", "start_date", "end_date"],
      body: null,
      needsAuth: true,
    },
    {
      id: "sheets",
      method: "POST",
      path: `${API}/exports/google-sheets`,
      title: "Google Sheets export",
      description: "Upsert GMV and/or Sessions tabs into a spreadsheet.",
      headers: [
        "Authorization: Bearer &lt;access_token&gt; (required)",
        "Content-Type: application/json",
      ],
      query: [],
      body: '{ "property_id", "report_types", "start_date", "end_date", "spreadsheet_id" }',
      needsAuth: true,
    },
  ];

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }
  function $all(sel, root) {
    return Array.from((root || document).querySelectorAll(sel));
  }

  function toast(msg) {
    const el = $("#toast");
    el.textContent = msg;
    el.hidden = false;
    setTimeout(() => {
      el.hidden = true;
    }, 2200);
  }

  function defaultDateRange() {
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - 6);
    return {
      start: start.toISOString().slice(0, 10),
      end: end.toISOString().slice(0, 10),
    };
  }

  function setDefaultDates() {
    const { start, end } = defaultDateRange();
    for (const formId of ["reports-form", "sheets-form"]) {
      const form = document.getElementById(formId);
      if (!form) continue;
      if (form.start_date) form.start_date.value = start;
      if (form.end_date) form.end_date.value = end;
    }
  }

  function decodeJwtPayload(token) {
    try {
      const part = token.split(".")[1];
      const json = atob(part.replace(/-/g, "+").replace(/_/g, "/"));
      return JSON.parse(json);
    } catch {
      return null;
    }
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function syntaxHighlightJson(value) {
    const text =
      typeof value === "string" ? value : JSON.stringify(value, null, 2);
    const escaped = escapeHtml(text);
    return escaped.replace(
      /("(\\u[\da-fA-F]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
      (match) => {
        let cls = "jn";
        if (/^"/.test(match)) {
          cls = /:$/.test(match) ? "jk" : "js";
        } else if (/true|false/.test(match)) {
          cls = "jb";
        } else if (/null/.test(match)) {
          cls = "jl";
        }
        return `<span class="${cls}">${match}</span>`;
      }
    );
  }

  function setJsonPre(el, data) {
    if (typeof el === "string") el = document.getElementById(el);
    if (!el) return;
    if (data === undefined || data === null) {
      el.textContent = "—";
      el.classList.remove("json-highlight");
      return;
    }
    el.classList.add("json-highlight");
    el.innerHTML = syntaxHighlightJson(data);
  }

  function statusClass(ok, warn) {
    if (ok) return "ok";
    if (warn) return "warn";
    return "err";
  }

  function renderCards(container, items) {
    container.innerHTML = items
      .map(
        (item) => `
      <div class="card">
        <div class="card-label">${escapeHtml(item.label)}</div>
        <div class="card-value">
          ${item.dot !== false ? `<span class="status-dot ${item.status || ""}"></span>` : ""}
          ${escapeHtml(String(item.value ?? "—"))}
        </div>
      </div>`
      )
      .join("");
  }

  function updateTokenPill() {
    const pill = $("#token-pill");
    if (!session.accessToken) {
      pill.textContent = "No active token";
      pill.className = "token-pill";
      return;
    }
    const left = session.expiresAt ? Math.max(0, session.expiresAt - Math.floor(Date.now() / 1000)) : 0;
    pill.textContent = left > 0 ? `Token active · ${formatCountdown(left)}` : "Token expired";
    pill.className = "token-pill " + (left > 60 ? "ok" : "warn");
  }

  function formatCountdown(seconds) {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}m ${String(s).padStart(2, "0")}s`;
  }

  function startCountdown() {
    stopCountdown();
    countdownTimer = setInterval(() => {
      updateTokenPill();
      renderAuthCards();
      if (session.expiresAt && session.expiresAt <= Math.floor(Date.now() / 1000)) {
        stopCountdown();
      }
    }, 1000);
  }

  function stopCountdown() {
    if (countdownTimer) clearInterval(countdownTimer);
    countdownTimer = null;
  }

  function clearToken() {
    session.accessToken = null;
    session.expiresAt = null;
    session.scope = "";
    session.properties = [];
    session.expiresIn = null;
    stopCountdown();
    updateTokenPill();
    renderAuthCards();
    setJsonPre("auth-response-json", null);
    toast("Token cleared from memory");
  }

  function authHeaders() {
    if (!session.accessToken) return {};
    return { Authorization: `Bearer ${session.accessToken}` };
  }

  async function requestRaw(method, url, options = {}) {
    const headers = { ...(options.headers || {}) };
  const init = { method, headers, signal: options.signal };
    if (options.body !== undefined) init.body = options.body;
    const t0 = performance.now();
    const res = await fetch(url, init);
    const ms = Math.round(performance.now() - t0);
    const contentType = res.headers.get("content-type") || "";
    let data;
    const text = await res.text();
    if (contentType.includes("application/json")) {
      try {
        data = text ? JSON.parse(text) : null;
      } catch {
        data = { _raw: text };
      }
    } else {
      data = text || null;
    }
    return { status: res.status, ms, data, ok: res.ok };
  }

  function reportParamsFromForms() {
    const form = $("#reports-form");
    return {
      property_id: form.property_id.value.trim(),
      start_date: form.start_date.value,
      end_date: form.end_date.value,
    };
  }

  async function fetchHealth() {
    if (!session.accessToken) {
      toast("Generate a JWT first (Authentication)");
      return null;
    }
    const btn = $("#btn-refresh-health");
    btn.disabled = true;
    btn.classList.add("loading");
    try {
      const result = await requestRaw("GET", `${API}/health`, { headers: authHeaders() });
      const checkedAt = new Date().toISOString();
      renderOverview(result.data, checkedAt, result.status);
      setJsonPre("overview-health-json", result.data ?? { error: result.status });
      if (!result.ok) toast(`Health request failed (${result.status})`);
      return result;
    } finally {
      btn.disabled = false;
      btn.classList.remove("loading");
    }
  }

  function renderOverview(health, checkedAt, httpStatus) {
    const container = $("#overview-cards");
    const tokenOk =
      session.accessToken && session.expiresAt && session.expiresAt > Math.floor(Date.now() / 1000);
    const mcp = health && health.mcp ? health.mcp : {};
    const connectorOk = health && health.status === "ok";
    const items = [
      {
        label: "HTTP status",
        value: httpStatus ?? "—",
        status: httpStatus === 200 ? "ok" : "err",
      },
      {
        label: "Connector",
        value: health ? health.connector : "unknown",
        status: health && health.connector === "ok" ? "ok" : "warn",
      },
      {
        label: "Overall status",
        value: health ? health.status : "—",
        status: statusClass(connectorOk, !connectorOk && health),
      },
      {
        label: "MCP connected",
        value: mcp.connected ? "Yes" : "No",
        status: mcp.connected ? "ok" : "err",
      },
      {
        label: "run_report tool",
        value: mcp.run_report_available ? "Available" : "Unavailable",
        status: mcp.run_report_available ? "ok" : "warn",
      },
      {
        label: "Authentication",
        value: tokenOk ? "JWT active" : session.accessToken ? "JWT expired" : "No token",
        status: tokenOk ? "ok" : session.accessToken ? "warn" : "err",
      },
      {
        label: "API service",
        value: httpStatus === 200 ? "Reachable" : "Error",
        status: httpStatus === 200 ? "ok" : "err",
      },
      {
        label: "Last health check",
        value: checkedAt,
        dot: false,
      },
    ];
    if (mcp.error_message) {
      items.push({
        label: "MCP error",
        value: mcp.error_message,
        dot: false,
        status: "err",
      });
    }
    renderCards(container, items);
  }

  function renderAuthCards() {
    const container = $("#auth-cards");
    if (!session.accessToken) {
      container.innerHTML = "";
      return;
    }
    const left = session.expiresAt
      ? Math.max(0, session.expiresAt - Math.floor(Date.now() / 1000))
      : 0;
    renderCards(container, [
      { label: "Token type", value: session.tokenType, dot: false },
      { label: "Expires in (sec)", value: session.expiresIn, dot: false },
      {
        label: "Countdown",
        value: left > 0 ? formatCountdown(left) : "Expired",
        status: left > 60 ? "ok" : "warn",
      },
      { label: "Scopes", value: session.scope || "—", dot: false },
      {
        label: "Property IDs",
        value: session.properties.length ? session.properties.join(", ") : "—",
        dot: false,
      },
    ]);
    updateTokenPill();
  }

  async function submitAuthForm(ev) {
    ev.preventDefault();
    const form = ev.target;
    const clientId = form.client_id.value.trim();
    const clientSecret = form.client_secret.value;
    if (!clientId || !clientSecret) return;

    const body = new URLSearchParams({
      grant_type: "client_credentials",
      client_id: clientId,
      client_secret: clientSecret,
    });

    const btn = form.querySelector('[type="submit"]');
    btn.disabled = true;
    btn.classList.add("loading");
    try {
      const result = await requestRaw("POST", `${API}/auth/token`, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      const display = { status: result.status, duration_ms: result.ms, body: result.data };
      setJsonPre("auth-response-json", display);

      if (!result.ok || !result.data || !result.data.access_token) {
        toast(result.data?.detail || `Token request failed (${result.status})`);
        return;
      }

      session.accessToken = result.data.access_token;
      session.tokenType = result.data.token_type || "Bearer";
      session.expiresIn = result.data.expires_in;
      session.scope = result.data.scope || "";
      const claims = decodeJwtPayload(session.accessToken);
      session.expiresAt = claims && claims.exp ? claims.exp : Math.floor(Date.now() / 1000) + (session.expiresIn || 0);
      session.properties = claims && Array.isArray(claims.properties) ? claims.properties : [];
      session.issuedAt = claims && claims.iat ? claims.iat : null;

      form.client_secret.value = "";
      renderAuthCards();
      startCountdown();

      if (claims && claims.properties && claims.properties[0]) {
        const pid = claims.properties[0];
        const reports = $("#reports-form");
        const sheets = $("#sheets-form");
        if (reports && !reports.property_id.value) reports.property_id.value = pid;
        if (sheets && !sheets.property_id.value) sheets.property_id.value = pid;
      }

      toast("Access token issued (memory only)");
    } finally {
      btn.disabled = false;
      btn.classList.remove("loading");
    }
  }

  function setReportsAlert(msg, kind) {
    const el = $("#reports-alert");
    if (!msg) {
      el.hidden = true;
      return;
    }
    el.hidden = false;
    el.textContent = msg;
    el.className = "alert" + (kind === "info" ? " info" : "");
  }

  function renderReportStats(gmvResp, sessionsResp) {
    const stats = $("#reports-stats");
    const parts = [];
    if (gmvResp) {
      const rows = gmvResp.data || [];
      const totalGmv = rows.reduce((s, r) => s + (Number(r.gmv) || 0), 0);
      parts.push(`GMV rows: ${rows.length} · Total GMV: ${totalGmv.toFixed(2)} ${gmvResp.currency || ""}`.trim());
    }
    if (sessionsResp) {
      const rows = sessionsResp.data || [];
      const totalSessions = rows.reduce((s, r) => s + (Number(r.sessions) || 0), 0);
      parts.push(`Session rows: ${rows.length} · Total sessions: ${totalSessions}`);
    }
    stats.textContent = parts.join(" | ");
  }

  function formatDisplayDate(isoDate) {
    const parts = String(isoDate || "").trim().split("-");
    if (parts.length !== 3) return isoDate || "—";
    const y = Number(parts[0]);
    const m = Number(parts[1]);
    const d = Number(parts[2]);
    if (!y || !m || !d) return isoDate;
    const dt = new Date(Date.UTC(y, m - 1, d));
    return new Intl.DateTimeFormat("en-GB", {
      day: "numeric",
      month: "long",
      year: "numeric",
      timeZone: "UTC",
    }).format(dt);
  }

  function formatGmv(value) {
    return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(Number(value) || 0);
  }

  function formatSessions(value) {
    return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(Number(value) || 0);
  }

  /**
   * Group API rows by date (descending). Each group: { date, entries: [{source, value}], total }.
   */
  function buildDateGroups(apiRows, metricKey) {
    const byDate = new Map();
    for (const row of apiRows || []) {
      const date = String(row.date || "").trim();
      if (!date) continue;
      const rawSource = row.source;
      const source =
        rawSource != null && String(rawSource).trim() !== ""
          ? String(rawSource).trim()
          : "—";
      const value = Number(row[metricKey]);
      const safeValue = Number.isFinite(value) ? value : 0;
      if (!byDate.has(date)) byDate.set(date, []);
      byDate.get(date).push({ source, value: safeValue });
    }
    const dates = Array.from(byDate.keys()).sort((a, b) => b.localeCompare(a));
    return dates.map((date) => {
      const entries = byDate.get(date);
      entries.sort((a, b) => a.source.localeCompare(b.source, undefined, { sensitivity: "base" }));
      const total = entries.reduce((sum, e) => sum + e.value, 0);
      return { date, entries, total };
    });
  }

  function updateReportSummary(kind, groups) {
    const el = document.getElementById(kind === "gmv" ? "gmv-summary" : "sessions-summary");
    if (!el) return;
    const recordCount = groups.reduce((n, g) => n + g.entries.length, 0);
    el.textContent = groups.length ? `${groups.length} days · ${recordCount} records` : "";
  }

  function renderDateGroupedReport(containerId, pagerKey, kind) {
    const container = document.getElementById(containerId);
    const state = tableState[pagerKey];
    const groups = state.groups || [];
    const metricLabel = kind === "gmv" ? "GMV" : "Sessions";

    if (!groups.length) {
      container.innerHTML = '<p class="report-empty">No rows in this date range.</p>';
      updateReportSummary(kind, []);
      return;
    }

    container.innerHTML = groups
      .map((group) => {
        const title = formatDisplayDate(group.date);
        const bodyRows = group.entries
          .map(
            (e) =>
              `<tr><td>${escapeHtml(e.source)}</td><td>${escapeHtml(
                kind === "gmv" ? formatGmv(e.value) : formatSessions(e.value)
              )}</td></tr>`
          )
          .join("");
        const totalCell = kind === "gmv" ? formatGmv(group.total) : formatSessions(group.total);
        return `
        <section class="date-section" data-date="${escapeHtml(group.date)}">
          <h3 class="date-section-title">${escapeHtml(title)}</h3>
          <table class="source-table">
            <thead><tr><th>Source</th><th>${metricLabel}</th></tr></thead>
            <tbody>
              ${bodyRows || `<tr><td colspan="2">No sources for this date.</td></tr>`}
              <tr class="row-total"><td>Daily Total</td><td>${escapeHtml(totalCell)}</td></tr>
            </tbody>
          </table>
        </section>`;
      })
      .join("");

    updateReportSummary(kind, groups);
  }

  function setGmvReportData(resp) {
    tableState.gmv.currency = resp.currency || "";
    tableState.gmv.groups = buildDateGroups(resp.data, "gmv");
    renderDateGroupedReport("gmv-by-date", "gmv", "gmv");
  }

  function setSessionsReportData(resp) {
    tableState.sessions.groups = buildDateGroups(resp.data, "sessions");
    renderDateGroupedReport("sessions-by-date", "sessions", "sessions");
  }

  async function fetchReport(kind) {
    if (!session.accessToken) {
      toast("Generate a JWT first");
      return null;
    }
    const params = reportParamsFromForms();
    if (!params.property_id || !params.start_date || !params.end_date) {
      setReportsAlert("Set property ID and date range.");
      return null;
    }
    setReportsAlert("Loading…", "info");
    const q = new URLSearchParams(params);
    const path =
      kind === "gmv"
        ? `${API}/reports/gmv-by-source?${q}`
        : `${API}/reports/sessions-by-source?${q}`;
    const result = await requestRaw("GET", path, { headers: authHeaders() });
    if (!result.ok) {
      const detail =
        typeof result.data === "object" && result.data
          ? result.data.detail || JSON.stringify(result.data)
          : `HTTP ${result.status}`;
      setReportsAlert(String(detail));
      return null;
    }
    setReportsAlert("");
    return result.data;
  }

  async function runReports(mode) {
    const buttons = $all("#reports-form [data-report]");
    buttons.forEach((b) => (b.disabled = true));
    try {
      let gmv = null;
      let sessions = null;
      if (mode === "gmv" || mode === "both") {
        gmv = await fetchReport("gmv");
        if (gmv) {
          $("#gmv-block").hidden = false;
          setGmvReportData(gmv);
        }
      }
      if (mode === "sessions" || mode === "both") {
        sessions = await fetchReport("sessions");
        if (sessions) {
          $("#sessions-block").hidden = false;
          setSessionsReportData(sessions);
        }
      }
      renderReportStats(gmv, sessions);
    } finally {
      buttons.forEach((b) => (b.disabled = false));
    }
  }

  function buildApiExplorer() {
    const root = $("#api-endpoints");
    root.innerHTML = ENDPOINTS.map((ep) => {
      const methodClass = ep.method === "POST" ? "post" : "";
      const fields =
        ep.query.length > 0
          ? `<div class="api-fields" data-ep="${ep.id}">
            <label>property_id<input type="text" name="property_id" /></label>
            <label>start_date<input type="date" name="start_date" /></label>
            <label>end_date<input type="date" name="end_date" /></label>
          </div>`
          : ep.id === "sheets"
            ? `<div class="api-fields form-grid" data-ep="${ep.id}">
            <label>property_id<input type="text" name="property_id" /></label>
            <label>start_date<input type="date" name="start_date" /></label>
            <label>end_date<input type="date" name="end_date" /></label>
            <label>spreadsheet_id<input type="text" name="spreadsheet_id" /></label>
            <label class="checkbox-row"><input type="checkbox" name="gmv" checked /> gmv_by_source</label>
            <label class="checkbox-row"><input type="checkbox" name="sessions" checked /> sessions_by_source</label>
          </div>`
            : ep.id === "token"
              ? `<div class="api-fields form-grid" data-ep="${ep.id}">
              <label>client_id<input type="text" name="client_id" /></label>
              <label>client_secret<input type="password" name="client_secret" /></label>
            </div>`
              : "";
      return `
      <article class="api-card" data-endpoint="${ep.id}">
        <h3><span class="method ${methodClass}">${ep.method}</span> ${escapeHtml(ep.path)}</h3>
        <p>${escapeHtml(ep.description)}</p>
        <div class="api-meta">
          <div><strong>Headers:</strong> ${ep.headers.map(escapeHtml).join("; ")}</div>
          ${ep.query.length ? `<div><strong>Query:</strong> ${ep.query.map((q) => `<code>${escapeHtml(q)}</code>`).join(", ")}</div>` : ""}
          ${ep.body ? `<div><strong>Body:</strong> <code>${escapeHtml(ep.body)}</code></div>` : ""}
        </div>
        ${fields}
        <div class="form-actions">
          <button type="button" class="btn btn-primary btn-sm" data-exec="${ep.id}">Execute</button>
          <button type="button" class="btn btn-ghost btn-sm" data-copy-url="${ep.id}">Copy URL</button>
          <button type="button" class="btn btn-ghost btn-sm" data-copy-body="${ep.id}">Copy body</button>
          <button type="button" class="btn btn-ghost btn-sm" data-copy-res="${ep.id}">Copy response</button>
        </div>
        <div class="api-result" id="api-result-${ep.id}"></div>
        <pre class="json-view" id="api-json-${ep.id}">—</pre>
      </article>`;
    }).join("");

    const { start, end } = defaultDateRange();
    $all(".api-fields").forEach((box) => {
      const sd = box.querySelector('[name="start_date"]');
      const ed = box.querySelector('[name="end_date"]');
      if (sd) sd.value = start;
      if (ed) ed.value = end;
    });
  }

  function apiUrlFor(ep) {
    const card = document.querySelector(`[data-endpoint="${ep.id}"]`);
    const fields = card && card.querySelector(".api-fields");
    if (ep.method === "GET" && fields) {
      const q = new URLSearchParams({
        property_id: fields.property_id?.value.trim() || "",
        start_date: fields.start_date?.value || "",
        end_date: fields.end_date?.value || "",
      });
      return `${ep.path}?${q}`;
    }
    return ep.path;
  }

  function apiBodyFor(ep) {
    const card = document.querySelector(`[data-endpoint="${ep.id}"]`);
    const fields = card && card.querySelector(".api-fields");
    if (ep.id === "token" && fields) {
      return new URLSearchParams({
        grant_type: "client_credentials",
        client_id: fields.client_id.value.trim(),
        client_secret: fields.client_secret.value,
      }).toString();
    }
    if (ep.id === "sheets" && fields) {
      const types = [];
      if (fields.querySelector('[name="gmv"]')?.checked) types.push("gmv_by_source");
      if (fields.querySelector('[name="sessions"]')?.checked) types.push("sessions_by_source");
      return JSON.stringify({
        property_id: fields.property_id.value.trim(),
        start_date: fields.start_date.value,
        end_date: fields.end_date.value,
        spreadsheet_id: fields.spreadsheet_id.value.trim(),
        report_types: types,
      });
    }
    return "";
  }

  async function executeEndpoint(epId) {
    const ep = ENDPOINTS.find((e) => e.id === epId);
    if (!ep) return;
    if (ep.needsAuth && !session.accessToken && ep.id !== "token") {
      toast("No Bearer token in memory — expect 401/403");
    }
    const url = apiUrlFor(ep);
    const headers = {};
    let body;
    if (ep.id === "token") {
      headers["Content-Type"] = "application/x-www-form-urlencoded";
      body = apiBodyFor(ep);
    } else if (ep.method === "POST") {
      headers["Content-Type"] = "application/json";
      headers.Authorization = `Bearer ${session.accessToken}`;
      body = apiBodyFor(ep);
    } else {
      Object.assign(headers, authHeaders());
    }
    const result = await requestRaw(ep.method, url, { headers, body });
    const meta = document.getElementById(`api-result-${ep.id}`);
    meta.innerHTML = `<span><strong>Status:</strong> ${result.status}</span><span><strong>Time:</strong> ${result.ms} ms</span>`;
    setJsonPre(`api-json-${ep.id}`, result.data);
    cardStoreResponse(ep.id, result.data);
    if (!result.ok) toast(`Request failed (${result.status})`);
  }

  const apiResponseCache = {};

  function cardStoreResponse(id, data) {
    apiResponseCache[id] = data;
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      toast("Copied");
    } catch {
      toast("Copy failed");
    }
  }

  function onCopyTargetClick(ev) {
    const id = ev.target.getAttribute("data-copy-target");
    const el = document.getElementById(id);
    if (!el) return;
    const plain = el.textContent || "";
    copyText(plain);
  }

  async function submitSheets(ev) {
    ev.preventDefault();
    const form = ev.target;
    if (!session.accessToken) {
      toast("Generate a JWT first");
      return;
    }
    const types = [];
    if (form.gmv.checked) types.push("gmv_by_source");
    if (form.sessions.checked) types.push("sessions_by_source");
    if (!types.length) {
      toast("Select at least one report type");
      return;
    }
    const payload = {
      property_id: form.property_id.value.trim(),
      start_date: form.start_date.value,
      end_date: form.end_date.value,
      spreadsheet_id: form.spreadsheet_id.value.trim(),
      report_types: types,
    };
    const btn = form.querySelector('[type="submit"]');
    btn.disabled = true;
    btn.classList.add("loading");
    try {
      const result = await requestRaw("POST", `${API}/exports/google-sheets`, {
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setJsonPre("sheets-response-json", { status: result.status, duration_ms: result.ms, body: result.data });
      const data = result.data;
      const cards = $("#sheets-cards");
      if (data && typeof data === "object" && data.success !== false) {
        const reportLines = (data.reports || [])
          .map(
            (r) =>
              `${r.report_type}: exported ${r.rows_exported}, inserted ${r.rows_inserted}, updated ${r.rows_updated}, total ${r.rows_total}`
          )
          .join(" · ");
        renderCards(cards, [
          { label: "Success", value: data.success ? "Yes" : "No", status: data.success ? "ok" : "err" },
          { label: "Spreadsheet", value: data.spreadsheet_url || data.spreadsheet_id, dot: false },
          { label: "Synced at", value: data.synced_at || "—", dot: false },
          { label: "Reports", value: reportLines || "—", dot: false },
        ]);
      } else {
        cards.innerHTML = "";
      }
      if (!result.ok) toast(`Export failed (${result.status})`);
      else toast("Export completed");
    } finally {
      btn.disabled = false;
      btn.classList.remove("loading");
    }
  }

  function switchSection(name) {
    const titles = {
      overview: "Overview",
      auth: "Authentication",
      reports: "Report Explorer",
      api: "API Explorer",
      sheets: "Google Sheets Export",
    };
    $("#section-title").textContent = titles[name] || name;
    $all(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.section === name));
    $all(".panel").forEach((p) => p.classList.toggle("visible", p.dataset.panel === name));
    if (name === "overview" && session.accessToken) fetchHealth();
  }

  function bindNav() {
    $all(".nav-item").forEach((btn) => {
      btn.addEventListener("click", () => switchSection(btn.dataset.section));
    });
    $("#btn-refresh-health").addEventListener("click", () => fetchHealth());
    $("#auth-form").addEventListener("submit", submitAuthForm);
    $("#btn-clear-token").addEventListener("click", clearToken);
    $all("#reports-form [data-report]").forEach((btn) => {
      btn.addEventListener("click", () => runReports(btn.dataset.report));
    });
    document.addEventListener("click", (ev) => {
      const copyBtn = ev.target.closest("[data-copy-target]");
      if (copyBtn) onCopyTargetClick({ target: copyBtn });
      const exec = ev.target.closest("[data-exec]");
      if (exec) executeEndpoint(exec.dataset.exec);
      const copyUrl = ev.target.closest("[data-copy-url]");
      if (copyUrl) {
        const ep = ENDPOINTS.find((e) => e.id === copyUrl.dataset.copyUrl);
        if (ep) copyText(apiUrlFor(ep));
      }
      const copyBody = ev.target.closest("[data-copy-body]");
      if (copyBody) {
        const ep = ENDPOINTS.find((e) => e.id === copyBody.dataset.copyBody);
        if (ep) copyText(apiBodyFor(ep) || "(no body)");
      }
      const copyRes = ev.target.closest("[data-copy-res]");
      if (copyRes) {
        const cached = apiResponseCache[copyRes.dataset.copyRes];
        copyText(cached ? JSON.stringify(cached, null, 2) : "");
      }
    });
    $("#sheets-form").addEventListener("submit", submitSheets);
  }

  function init() {
    setDefaultDates();
    buildApiExplorer();
    bindNav();
    updateTokenPill();
    renderOverview(null, "—", null);
  }

  init();
})();