import logging
from typing import Any

from src.config.dates import ResolvedDateRange
from src.dashboard.repository import _aggregate_rows
from src.reports.gmv_by_channel import fetch_gmv_by_channel
from src.reports.sessions_by_channel import fetch_sessions_by_channel

logger = logging.getLogger(__name__)


def _safe_fetch(fetcher, date_range: ResolvedDateRange) -> dict[str, Any]:
    try:
        return fetcher(date_range)
    except ValueError as exc:
        logger.warning("Report empty or invalid for %s: %s", date_range.label_start, exc)
        return {"data": [], "property_id": None, "currency": None}
    except Exception:
        logger.exception("GA4 channel report failed")
        raise


def get_channel_dashboard(start_date: str, end_date: str) -> dict[str, Any]:
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date.")

    date_range = ResolvedDateRange(
        start_date=start_date,
        end_date=end_date,
        label_start=start_date,
        label_end=end_date,
    )

    gmv_payload = _safe_fetch(fetch_gmv_by_channel, date_range)
    sessions_payload = _safe_fetch(fetch_sessions_by_channel, date_range)

    property_id = gmv_payload.get("property_id") or sessions_payload.get("property_id")
    currency = gmv_payload.get("currency")

    gmv_rows = _aggregate_rows(
        gmv_payload,
        start_date=start_date,
        end_date=end_date,
        metric_key="gmv",
    )
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
        "source": "ga4_live",
    }