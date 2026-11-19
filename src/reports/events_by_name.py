import logging
from typing import Any

from src.clients.analytics_client import (
    EVENT_DIMENSION,
    EVENT_SUMMARY_METRICS,
    DATE_DIMENSION,
    extract_currency,
    parse_dimension_metric_rows,
    run_report_query,
)
from src.config.dates import ResolvedDateRange
from src.reports.output import build_report_payload, write_report_json

logger = logging.getLogger(__name__)

REPORT_TYPE = "events_by_name"
FILENAME_STEM = "events_by_name"

SUMMARY_METRIC_KEYS = [
    "sessions",
    "event_count",
    "total_users",
    "event_count_per_user",
    "total_revenue",
]


def _snake_metrics() -> list[str]:
    return SUMMARY_METRIC_KEYS


def fetch_events_by_name(date_range: ResolvedDateRange) -> dict[str, Any]:
    start = date_range.start_date
    end = date_range.end_date

    summary_response, property_id = run_report_query(
        dimensions=[EVENT_DIMENSION],
        metrics=EVENT_SUMMARY_METRICS,
        start_date=start,
        end_date=end,
    )
    daily_response, _ = run_report_query(
        dimensions=[DATE_DIMENSION, EVENT_DIMENSION],
        metrics=["sessions", "eventCount"],
        start_date=start,
        end_date=end,
    )

    currency = extract_currency(summary_response) or extract_currency(daily_response)

    summary = parse_dimension_metric_rows(
        summary_response,
        dimension_keys=["event_name"],
        metric_keys=_snake_metrics(),
    )
    daily = parse_dimension_metric_rows(
        daily_response,
        dimension_keys=["date", "event_name"],
        metric_keys=["sessions", "event_count"],
    )

    payload = build_report_payload(
        property_id=property_id,
        report_type=REPORT_TYPE,
        start_date=date_range.label_start,
        end_date=date_range.label_end,
        currency=currency,
        data=[],
    )
    payload["summary"] = summary
    payload["daily"] = daily
    logger.info(
        "Events by name: %s events, %s daily rows",
        len(summary),
        len(daily),
    )
    return payload


def run_and_save_events_by_name(date_range: ResolvedDateRange):
    payload = fetch_events_by_name(date_range)
    path = write_report_json(payload, FILENAME_STEM)
    summary_count = len(payload["summary"])
    return payload, path, summary_count