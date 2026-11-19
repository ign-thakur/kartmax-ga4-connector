let timeChart;
let barChart;
let datePicker;
let debounceTimer;

function showStatus(msg) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.style.display = msg ? "block" : "none";
}

function formatMoney(value, currency) {
  const code = currency || "INR";
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: code,
      maximumFractionDigits: 2,
    }).format(Number(value));
  } catch {
    return Number(value).toLocaleString();
  }
}

function formatNum(value, digits = 2) {
  return Number(value).toLocaleString(undefined, {
    maximumFractionDigits: digits,
  });
}

function renderTimeChart(series) {
  const ctx = document.getElementById("timeChart");
  if (timeChart) timeChart.destroy();
  const labels = series.map((r) => formatShortDate(r.date));
  timeChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "purchase",
          data: series.map((r) => r.sessions),
          borderColor: "#1a73e8",
          backgroundColor: "#1a73e8",
          pointRadius: series.length === 1 ? 6 : 3,
          tension: 0.2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: true, position: "bottom" } },
      scales: {
        y: { beginAtZero: true, ticks: { color: "#5f6368" }, grid: { color: "rgba(0,0,0,0.08)" } },
        x: { ticks: { color: "#5f6368" }, grid: { color: "rgba(0,0,0,0.08)" } },
      },
    },
  });
}

function formatShortDate(iso) {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function renderBarChart(tableRows) {
  const ctx = document.getElementById("barChart");
  if (barChart) barChart.destroy();
  const top = tableRows.slice(0, 8);
  barChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: top.map((r) => r.event_name),
      datasets: [
        {
          label: "Sessions",
          data: top.map((r) => r.sessions),
          backgroundColor: "#1a73e8",
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { beginAtZero: true, ticks: { color: "#5f6368" }, grid: { color: "rgba(0,0,0,0.08)" } },
        y: { ticks: { color: "#5f6368", font: { size: 12 } }, grid: { display: false } },
      },
    },
  });
}

function renderTable(rows, currency) {
  const tbody = document.getElementById("eventTableBody");
  if (!rows.length) {
    tbody.innerHTML =
      '<tr><td colspan="6">No events match this search for the selected range.</td></tr>';
    return;
  }
  tbody.innerHTML = rows
    .map(
      (r, i) => `<tr class="${i % 2 === 0 ? "shaded" : ""}">
      <td><a class="dim-link" href="#">${r.event_name}</a></td>
      <td class="num">${formatNum(r.sessions, 0)}<span class="pct">${r.sessions_pct}</span></td>
      <td class="num">${formatNum(r.event_count, 0)}<span class="pct">${r.event_count_pct}</span></td>
      <td class="num">${formatNum(r.total_users, 0)}<span class="pct">${r.total_users_pct}</span></td>
      <td class="num">${formatNum(r.event_count_per_user)}</td>
      <td class="num">${formatMoney(r.total_revenue, currency)}<span class="pct">${r.total_revenue_pct}</span></td>
    </tr>`
    )
    .join("");
}

async function loadEvents(start, end) {
  const search = document.getElementById("eventSearch").value.trim();
  showStatus("");
  const params = new URLSearchParams({
    start_date: start,
    end_date: end,
    search,
  });
  const res = await fetch(`/api/events?${params}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    showStatus(err.detail || "Failed to load events.");
    return;
  }
  const data = await res.json();
  document.getElementById("tableRange").textContent = `${data.table.length} events · ${data.start_date} → ${data.end_date}`;
  renderTimeChart(data.time_series);
  renderBarChart(data.table);
  renderTable(data.table, data.currency);
}

function todayIso() {
  const d = new Date();
  return d.toISOString().slice(0, 10);
}

function isoDate(d) {
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

async function init() {
  const res = await fetch("/api/range");
  const range = await res.json();
  const selectableMax = GADateRangeStorage.selectableMaxDate(range);

  datePicker = new GADateRangePicker({
    onApply: ({ start, end }) => loadEvents(start, end),
  });
  datePicker.setBounds(
    GADateRangeStorage.selectableMinDate(),
    selectableMax,
    range.data_min_date || range.min_date,
    range.data_max_date || range.max_date
  );

  const initial = GADateRangeStorage.resolveInitialRange(range);
  if (!initial) {
    showStatus("Unable to resolve date range. Run channel or events reports first.");
    return;
  }
  datePicker.setRange(initial.start, initial.end, initial.preset);
  await loadEvents(initial.start, initial.end);

  document.getElementById("eventSearch").addEventListener("input", () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      if (datePicker.start && datePicker.end) {
        loadEvents(isoDate(datePicker.start), isoDate(datePicker.end));
      }
    }, 400);
  });
}

init();