import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.config.settings import OUTPUT_DIR

_SAFE_NAME = re.compile(r"^[a-zA-Z0-9_.-]+\.json$")

REPORT_GMV = "gmv_by_channel"
REPORT_SESSIONS = "sessions_by_channel"


def _validate_filename(filename: str) -> Path:
    if not _SAFE_NAME.match(filename):
        raise ValueError("Invalid report filename.")
    path = (OUTPUT_DIR / filename).resolve()
    if not path.is_relative_to(OUTPUT_DIR.resolve()):
        raise ValueError("Invalid report path.")
    if not path.is_file():
        raise FileNotFoundError(f"Report not found: {filename}")
    return path


def list_reports() -> list[dict[str, Any]]:
    if not OUTPUT_DIR.exists():
        return []

    summaries: list[dict[str, Any]] = []
    for path in sorted(OUTPUT_DIR.glob("*.json"), reverse=True):
        try:
            with path.open(encoding="utf-8") as fh:
                payload = json.load(fh)
        except (json.JSONDecodeError, OSError):
            summaries.append(
                {
                    "filename": path.name,
                    "report_type": "unknown",
                    "start_date": None,
                    "end_date": None,
                    "generated_at": None,
                    "row_count": 0,
                    "currency": None,
                }
            )
            continue

        summaries.append(
            {
                "filename": path.name,
                "report_type": payload.get("report_type"),
                "start_date": payload.get("start_date"),
                "end_date": payload.get("end_date"),
                "generated_at": payload.get("generated_at"),
                "row_count": len(payload.get("data") or []),
                "currency": payload.get("currency"),
            }
        )
    return summaries


def load_report(filename: str) -> dict[str, Any]:
    path = _validate_filename(filename)
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _latest_report_filename(report_type: str) -> str | None:
    for summary in list_reports():
        if summary.get("report_type") == report_type:
            return summary["filename"]
    return None


def _aggregate_rows(
    payload: dict[str, Any],
    *,
    start_date: str,
    end_date: str,
    metric_key: str,
) -> list[dict[str, Any]]:
    totals: dict[str, float] = {}
    for row in payload.get("data") or []:
        day = row.get("date")
        if not day or day < start_date or day > end_date:
            continue
        channel = row.get("channel") or "(not set)"
        raw = row.get(metric_key)
        if raw is None:
            continue
        totals[channel] = totals.get(channel, 0.0) + float(raw)

    result = [
        {"channel": channel, metric_key: value}
        for channel, value in totals.items()
    ]
    reverse = metric_key == "gmv"
    result.sort(key=lambda item: item[metric_key], reverse=reverse)
    return result


def _default_date_window(dates: list[str]) -> tuple[str, str]:
    """Last 7 days ending at the newest available export day."""
    end = dates[-1]
    start_dt = datetime.strptime(end, "%Y-%m-%d") - timedelta(days=6)
    start = start_dt.strftime("%Y-%m-%d")
    if start < dates[0]:
        start = dates[0]
    return start, end


def get_available_range() -> dict[str, str | None]:
    """Union of dates present in the latest GMV and sessions exports."""
    dates: list[str] = []
    property_id = None
    for report_type in (REPORT_GMV, REPORT_SESSIONS):
        filename = _latest_report_filename(report_type)
        if not filename:
            continue
        payload = load_report(filename)
        if property_id is None:
            property_id = payload.get("property_id")
        for row in payload.get("data") or []:
            if row.get("date"):
                dates.append(row["date"])
    if not dates:
        return {
            "property_id": property_id,
            "min_date": None,
            "max_date": None,
            "default_start": None,
            "default_end": None,
        }
    dates.sort()
    default_start, default_end = _default_date_window(dates)
    return {
        "property_id": property_id,
        "min_date": dates[0],
        "max_date": dates[-1],
        "data_min_date": dates[0],
        "data_max_date": dates[-1],
        "default_start": default_start,
        "default_end": default_end,
    }


def get_dashboard_data(start_date: str, end_date: str) -> dict[str, Any]:
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date.")

    gmv_file = _latest_report_filename(REPORT_GMV)
    sessions_file = _latest_report_filename(REPORT_SESSIONS)
    if not gmv_file and not sessions_file:
        raise FileNotFoundError(
            "No report JSON found. Run gmv-by-channel and sessions-by-channel first."
        )

    property_id = None
    currency = None
    gmv_rows: list[dict[str, Any]] = []
    sessions_rows: list[dict[str, Any]] = []

    if gmv_file:
        gmv_payload = load_report(gmv_file)
        property_id = gmv_payload.get("property_id")
        currency = gmv_payload.get("currency")
        gmv_rows = _aggregate_rows(
            gmv_payload,
            start_date=start_date,
            end_date=end_date,
            metric_key="gmv",
        )

    if sessions_file:
        sessions_payload = load_report(sessions_file)
        property_id = property_id or sessions_payload.get("property_id")
        sessions_rows = _aggregate_rows(
            sessions_payload,
            start_date=start_date,
            end_date=end_date,
            metric_key="sessions",
        )

    return {
        "property_id": property_id,
        "start_date": start_date,
        "end_date": end_date,
        "currency": currency,
        "gmv_by_channel": gmv_rows,
        "sessions_by_channel": sessions_rows,
        "sources": {
            "gmv_report": gmv_file,
            "sessions_report": sessions_file,
        },
    }