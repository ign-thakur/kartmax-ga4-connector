from typing import Any

from src.config.dates import ResolvedDateRange
from src.reports.events_by_name import fetch_events_by_name


def _match_event(name: str, query: str) -> bool:
    return query.lower() in name.lower()


def _pct(part: float, whole: float) -> str:
    if whole <= 0:
        return "0%"
    return f"{round(100 * part / whole, 2)}%"


def get_events_view(
    start_date: str,
    end_date: str,
    search: str = "purchase",
) -> dict[str, Any]:
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date.")

    date_range = ResolvedDateRange(
        start_date=start_date,
        end_date=end_date,
        label_start=start_date,
        label_end=end_date,
    )
    payload = fetch_events_by_name(date_range)
    search = (search or "").strip()
    summary_rows = payload.get("summary") or []
    daily_rows = payload.get("daily") or []

    if search:
        summary_rows = [r for r in summary_rows if _match_event(r["event_name"], search)]
        daily_rows = [r for r in daily_rows if _match_event(r["event_name"], search)]

    summary_rows.sort(key=lambda r: float(r.get("sessions") or 0), reverse=True)

    total_sessions = sum(float(r.get("sessions") or 0) for r in summary_rows)
    total_event_count = sum(float(r.get("event_count") or 0) for r in summary_rows)
    total_users = sum(float(r.get("total_users") or 0) for r in summary_rows)
    total_revenue = sum(float(r.get("total_revenue") or 0) for r in summary_rows)

    table_rows = []
    for row in summary_rows:
        sessions = float(row.get("sessions") or 0)
        event_count = float(row.get("event_count") or 0)
        users = float(row.get("total_users") or 0)
        revenue = float(row.get("total_revenue") or 0)
        table_rows.append(
            {
                **row,
                "sessions_pct": _pct(sessions, total_sessions),
                "event_count_pct": _pct(event_count, total_event_count),
                "total_users_pct": _pct(users, total_users),
                "total_revenue_pct": _pct(revenue, total_revenue),
            }
        )

    series_map: dict[str, dict[str, float]] = {}
    for row in daily_rows:
        day = row["date"]
        sessions = float(row.get("sessions") or 0)
        series_map.setdefault(day, {"sessions": 0.0, "event_count": 0.0})
        series_map[day]["sessions"] += sessions
        series_map[day]["event_count"] += float(row.get("event_count") or 0)

    time_series = [
        {"date": day, **values}
        for day, values in sorted(series_map.items())
    ]

    return {
        "property_id": payload.get("property_id"),
        "start_date": start_date,
        "end_date": end_date,
        "currency": payload.get("currency"),
        "search": search,
        "time_series": time_series,
        "table": table_rows,
        "totals": {
            "sessions": total_sessions,
            "event_count": total_event_count,
            "total_users": total_users,
            "total_revenue": total_revenue,
        },
    }