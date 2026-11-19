/**
 * GA-style date range picker (presets + scrollable months).
 */
(function (global) {
  const STORAGE_KEY = "kartmax_ga4_date_range";

  const MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];

  function pad(n) {
    return String(n).padStart(2, "0");
  }

  function toKey(d) {
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  }

  function parseKey(key) {
    const [y, m, d] = key.split("-").map(Number);
    return new Date(y, m - 1, d);
  }

  function addDays(date, days) {
    const d = new Date(date);
    d.setDate(d.getDate() + days);
    return d;
  }

  function startOfMonth(d) {
    return new Date(d.getFullYear(), d.getMonth(), 1);
  }

  function endOfMonth(d) {
    return new Date(d.getFullYear(), d.getMonth() + 1, 0);
  }

  function startOfWeekSunday(d) {
    const x = new Date(d);
    x.setDate(x.getDate() - x.getDay());
    return x;
  }

  function formatDisplay(d) {
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function formatTrigger(start, end, presetLabel) {
    const short = (d) =>
      d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    const year = end.getFullYear();
    return `${presetLabel} ${short(start)} – ${short(end)}, ${year}`;
  }

  function formatTriggerRangeText(start, end) {
    const short = (d) =>
      d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    const year = end.getFullYear();
    return `${short(start)} - ${short(end)}, ${year}`;
  }

  function clampDate(d, min, max) {
    const t = d.getTime();
    if (min && t < min.getTime()) return new Date(min);
    if (max && t > max.getTime()) return new Date(max);
    return d;
  }

  const PRESETS = [
    { id: "custom", label: "Custom" },
    { id: "today", label: "Today" },
    { id: "yesterday", label: "Yesterday" },
    { id: "this_week", label: "This week (Sun – Today)" },
    { id: "last_7", label: "Last 7 days" },
    { id: "last_28", label: "Last 28 days" },
    { id: "last_30", label: "Last 30 days" },
    { id: "this_month", label: "This month" },
    { id: "last_month", label: "Last month" },
    { id: "last_90", label: "Last 90 days" },
    { id: "qtd", label: "Quarter to date" },
    { id: "this_year", label: "This year (Jan – Today)" },
    { id: "last_year", label: "Last calendar year" },
  ];

  function computePreset(id, today, bounds) {
    const max = bounds.max || today;
    const effectiveToday = clampDate(today, bounds.min, max);
    let start;
    let end;

    switch (id) {
      case "today":
        start = end = effectiveToday;
        break;
      case "yesterday": {
        const y = addDays(effectiveToday, -1);
        start = end = clampDate(y, bounds.min, max);
        break;
      }
      case "this_week":
        start = clampDate(startOfWeekSunday(effectiveToday), bounds.min, max);
        end = effectiveToday;
        break;
      case "last_7":
        start = clampDate(addDays(effectiveToday, -6), bounds.min, max);
        end = effectiveToday;
        break;
      case "last_28":
        start = clampDate(addDays(effectiveToday, -27), bounds.min, max);
        end = effectiveToday;
        break;
      case "last_30":
        start = clampDate(addDays(effectiveToday, -29), bounds.min, max);
        end = effectiveToday;
        break;
      case "this_month":
        start = clampDate(startOfMonth(effectiveToday), bounds.min, max);
        end = effectiveToday;
        break;
      case "last_month": {
        const prev = new Date(effectiveToday.getFullYear(), effectiveToday.getMonth() - 1, 1);
        start = clampDate(prev, bounds.min, max);
        end = clampDate(endOfMonth(prev), bounds.min, max);
        break;
      }
      case "last_90":
        start = clampDate(addDays(effectiveToday, -89), bounds.min, max);
        end = effectiveToday;
        break;
      case "qtd": {
        const qMonth = Math.floor(effectiveToday.getMonth() / 3) * 3;
        start = clampDate(new Date(effectiveToday.getFullYear(), qMonth, 1), bounds.min, max);
        end = effectiveToday;
        break;
      }
      case "this_year":
        start = clampDate(new Date(effectiveToday.getFullYear(), 0, 1), bounds.min, max);
        end = effectiveToday;
        break;
      case "last_year": {
        const y = effectiveToday.getFullYear() - 1;
        start = clampDate(new Date(y, 0, 1), bounds.min, max);
        end = clampDate(new Date(y, 11, 31), bounds.min, max);
        break;
      }
      default:
        return null;
    }
    if (start > end) start = end;
    return { start, end };
  }

  class GADateRangePicker {
    constructor(options) {
      this.bounds = { min: null, max: null };
      this.dataMin = null;
      this.dataMax = null;
      this.today = new Date();
      this.today.setHours(0, 0, 0, 0);
      this.start = null;
      this.end = null;
      this.activePreset = "custom";
      this.draftStart = null;
      this.draftEnd = null;
      this.awaitingEnd = false;
      this.onApply = options.onApply || (() => {});

      this.root = document.getElementById("gaDatePicker");
      this.trigger = document.getElementById("dateTrigger");
      this.triggerLabel = document.getElementById("triggerLabel");
      this.triggerPreset = document.getElementById("triggerPreset");
      this.triggerRange = document.getElementById("triggerRange");
      this.popover = document.getElementById("datePopover");
      this.backdrop = document.getElementById("dateBackdrop");
      this.startInput = document.getElementById("startDateInput");
      this.endInput = document.getElementById("endDateInput");
      this.monthsScroll = document.getElementById("monthsScroll");
      this.presetsEl = document.getElementById("presetsList");

      this._bind();
      this._renderPresets();
    }

    setBounds(minKey, maxKey, dataMinKey, dataMaxKey) {
      this.bounds.min = minKey ? parseKey(minKey) : null;
      this.bounds.max = maxKey ? parseKey(maxKey) : null;
      this.dataMin = dataMinKey ? parseKey(dataMinKey) : null;
      this.dataMax = dataMaxKey ? parseKey(dataMaxKey) : null;
      const now = new Date();
      now.setHours(0, 0, 0, 0);
      this.today = now;
    }

    setRange(startKey, endKey, presetId = "custom") {
      this.start = parseKey(startKey);
      this.end = parseKey(endKey);
      this.activePreset = presetId;
      this._syncDraft();
      this._updateTrigger();
    }

    _bind() {
      this.trigger.addEventListener("click", () => this.open());
      /* backdrop does not cancel — avoids losing partial range selection */
      document.getElementById("cancelBtn").addEventListener("click", () => this.cancel());
      document.getElementById("applyBtn").addEventListener("click", () => this.apply());
      const onInput = (which) => () => this._inputToDraft(which);
      this.startInput.addEventListener("change", onInput("start"));
      this.endInput.addEventListener("change", onInput("end"));
      this.startInput.addEventListener("blur", onInput("start"));
      this.endInput.addEventListener("blur", onInput("end"));
    }

    _renderPresets() {
      this.presetsEl.innerHTML = PRESETS.map(
        (p) =>
          `<button type="button" class="ga-preset" data-preset="${p.id}">${p.label}</button>`
      ).join("");
      this.presetsEl.querySelectorAll(".ga-preset").forEach((btn) => {
        btn.addEventListener("click", () => {
          const id = btn.dataset.preset;
          this.activePreset = id;
          this._highlightPreset();
          if (id === "custom") return;
          const range = computePreset(id, this.today, this.bounds);
          if (range) {
            this.draftStart = range.start;
            this.draftEnd = range.end;
            this.awaitingEnd = false;
            this._setRangeHint("Click Apply to load this range.");
            this._syncInputs();
            this._renderMonths();
          }
        });
      });
    }

    _highlightPreset() {
      this.presetsEl.querySelectorAll(".ga-preset").forEach((btn) => {
        btn.classList.toggle("active", btn.dataset.preset === this.activePreset);
      });
    }

    open() {
      this._syncDraft();
      this.activePreset = this.activePreset || "custom";
      this.awaitingEnd = false;
      this._highlightPreset();
      this._syncInputs();
      this._renderMonths();
      this._setRangeHint("Click a start date, then an end date.");
      this.popover.hidden = false;
      this.backdrop.hidden = false;
      this._scrollToSelection();
    }

    _setRangeHint(text) {
      const el = document.getElementById("rangeSelectHint");
      if (el) el.textContent = text;
    }

    cancel() {
      this.popover.hidden = true;
      this.backdrop.hidden = true;
      this._syncDraft();
    }

    apply() {
      if (!this.draftStart || !this.draftEnd) return;
      let s = this.draftStart;
      let e = this.draftEnd;
      if (s > e) [s, e] = [e, s];
      s = clampDate(s, this.bounds.min, this.bounds.max);
      e = clampDate(e, this.bounds.min, this.bounds.max);
      this.start = s;
      this.end = e;
      this._updateTrigger();
      this.popover.hidden = true;
      this.backdrop.hidden = true;
      const startKey = toKey(s);
      const endKey = toKey(e);
      saveSelectedRange(startKey, endKey, this.activePreset);
      this.onApply({ start: startKey, end: endKey });
    }

    _syncDraft() {
      this.draftStart = this.start ? new Date(this.start) : null;
      this.draftEnd = this.end ? new Date(this.end) : null;
      this.awaitingEnd = false;
    }

    _syncInputs() {
      if (this.draftStart) {
        this.startInput.value = formatDisplay(this.draftStart);
      }
      if (this.draftEnd) {
        this.endInput.value = formatDisplay(this.draftEnd);
      }
    }

    _inputToDraft(which) {
      this.activePreset = "custom";
      this._highlightPreset();
      const raw = which === "start" ? this.startInput.value : this.endInput.value;
      const parsed = new Date(raw);
      if (Number.isNaN(parsed.getTime())) return;
      parsed.setHours(0, 0, 0, 0);
      const clamped = clampDate(parsed, this.bounds.min, this.bounds.max);
      if (which === "start") this.draftStart = clamped;
      else this.draftEnd = clamped;
      if (this.draftStart && this.draftEnd && this.draftStart > this.draftEnd) {
        [this.draftStart, this.draftEnd] = [this.draftEnd, this.draftStart];
        this._syncInputs();
      }
      this.awaitingEnd = false;
      this._setRangeHint("Click Apply to load this range.");
      this._renderMonths();
    }

    _updateTrigger() {
      if (!this.start || !this.end) return;
      const preset = PRESETS.find((p) => p.id === this.activePreset);
      const label = preset ? preset.label : "Custom";
      if (this.triggerPreset && this.triggerRange) {
        this.triggerPreset.textContent = label;
        this.triggerRange.textContent = formatTriggerRangeText(
          this.start,
          this.end
        );
      } else if (this.triggerLabel) {
        this.triggerLabel.textContent = formatTrigger(
          this.start,
          this.end,
          label
        );
      }
    }

    _isDisabled(key) {
      const d = parseKey(key);
      if (this.bounds.min && d < this.bounds.min) return true;
      if (this.bounds.max && d > this.bounds.max) return true;
      return false;
    }

    _dayClass(key) {
      const classes = ["ga-day"];
      const d = parseKey(key);
      if (this._isDisabled(key)) {
        classes.push("disabled");
        return classes.join(" ");
      }
      if (this.dataMin && d < this.dataMin) {
        classes.push("before-data");
      }
      if (this.dataMax && d > this.dataMax) {
        classes.push("beyond-data");
      }
      const sk = this.draftStart ? toKey(this.draftStart) : null;
      const ek = this.draftEnd ? toKey(this.draftEnd) : null;
      if (toKey(this.today) === key) classes.push("today");
      if (sk && ek) {
        const start = this.draftStart;
        const end = this.draftEnd;
        const lo = start <= end ? start : end;
        const hi = start <= end ? end : start;
        if (key === toKey(lo)) classes.push("selected", "range-start");
        if (key === toKey(hi)) classes.push("selected", "range-end");
        if (d > lo && d < hi) classes.push("in-range");
        if (toKey(lo) === toKey(hi) && key === sk) {
          classes.push("selected", "range-start", "range-end");
        }
      }
      return classes.join(" ");
    }

    _onDayClick(key) {
      if (this._isDisabled(key)) return;
      this.activePreset = "custom";
      this._highlightPreset();
      const d = parseKey(key);
      if (this.awaitingEnd) {
        this.draftEnd = d;
        if (this.draftStart > this.draftEnd) {
          [this.draftStart, this.draftEnd] = [this.draftEnd, this.draftStart];
        }
        this.awaitingEnd = false;
        this._setRangeHint("Click Apply to load this range.");
      } else {
        this.draftStart = d;
        this.draftEnd = d;
        this.awaitingEnd = true;
        this._setRangeHint("Now click the end date (or Apply for a single day).");
      }
      this._syncInputs();
      this._renderMonths();
    }

    _renderMonths() {
      const min = this.bounds.min || addDays(this.today, -365);
      const max = this.bounds.max || this.today;
      let cursor = startOfMonth(min);
      const endMonth = startOfMonth(max);
      let html = "";

      while (cursor <= endMonth) {
        const year = cursor.getFullYear();
        const month = cursor.getMonth();
        const firstDow = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();

        html += `<div class="ga-month-block" data-month="${year}-${pad(month + 1)}">`;
        html += `<h3 class="ga-month-title">${MONTHS[month]} ${year}</h3>`;
        html += `<div class="ga-weekdays">${["S", "M", "T", "W", "T", "F", "S"]
          .map((w) => `<span>${w}</span>`)
          .join("")}</div>`;
        html += '<div class="ga-days">';

        for (let i = 0; i < firstDow; i++) {
          html += '<span class="ga-day empty"></span>';
        }
        for (let day = 1; day <= daysInMonth; day++) {
          const key = `${year}-${pad(month + 1)}-${pad(day)}`;
          const cls = this._dayClass(key);
          const dis = this._isDisabled(key) ? "disabled" : "";
          html += `<button type="button" class="${cls}" data-date="${key}" ${dis}>${day}</button>`;
        }
        html += "</div></div>";
        cursor = new Date(year, month + 1, 1);
      }

      this.monthsScroll.innerHTML = html;
      this.monthsScroll.querySelectorAll(".ga-day[data-date]").forEach((btn) => {
        btn.addEventListener("click", () => this._onDayClick(btn.dataset.date));
      });
    }

    _scrollToSelection() {
      const target = this.draftStart || this.draftEnd;
      if (!target) return;
      const key = `${target.getFullYear()}-${pad(target.getMonth() + 1)}`;
      const el = this.monthsScroll.querySelector(`[data-month="${key}"]`);
      if (el) el.scrollIntoView({ block: "center" });
    }
  }

  function saveSelectedRange(start, end, preset) {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ start, end, preset: preset || "custom" })
      );
    } catch {
      /* ignore quota / private mode */
    }
  }

  function loadSelectedRange() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  function todayIsoLocal() {
    const d = new Date();
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
  }

  /** GA4-style lookback — not tied to export file min (was locking calendar to Nov 1). */
  function selectableMinDate() {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    d.setMonth(d.getMonth() - 24);
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
  }

  /** Calendar may extend to today; channel JSON may end earlier (data_max_date). */
  function selectableMaxDate(apiRange) {
    const today = todayIsoLocal();
    const dataMax = apiRange.data_max_date || apiRange.max_date;
    if (!dataMax) return today;
    return dataMax >= today ? dataMax : today;
  }

  /** Prefer last Apply selection; else API default; validate against min/max. */
  function resolveInitialRange(apiRange, boundsMax) {
    const min = selectableMinDate();
    const max = boundsMax || selectableMaxDate(apiRange);
    if (!min || !max) {
      return null;
    }
    const saved = loadSelectedRange();
    if (
      saved &&
      saved.start >= min &&
      saved.end <= max &&
      saved.start <= saved.end
    ) {
      return {
        start: saved.start,
        end: saved.end,
        preset: saved.preset || "custom",
      };
    }
    if (apiRange.default_start && apiRange.default_end) {
      return {
        start: apiRange.default_start,
        end: apiRange.default_end,
        preset: "custom",
      };
    }
    return null;
  }

  global.GADateRangePicker = GADateRangePicker;
  global.GADateRangeStorage = {
    saveSelectedRange,
    loadSelectedRange,
    resolveInitialRange,
    selectableMinDate,
    selectableMaxDate,
    todayIsoLocal,
  };
})(window);