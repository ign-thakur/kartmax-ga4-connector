import logging
from typing import Any

from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
    RunReportResponse,
)

from src.auth.ga4_client import get_ga4_client

logger = logging.getLogger(__name__)

CHANNEL_DIMENSION = "sessionDefaultChannelGroup"
DATE_DIMENSION = "date"
EVENT_DIMENSION = "eventName"

EVENT_SUMMARY_METRICS = [
    "sessions",
    "eventCount",
    "totalUsers",
    "eventCountPerUser",
    "totalRevenue",
]


def run_channel_report(
    *,
    metric_name: str,
    start_date: str,
    end_date: str,
) -> tuple[RunReportResponse, str]:
    client, property_id = get_ga4_client()

    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=[
            Dimension(name=DATE_DIMENSION),
            Dimension(name=CHANNEL_DIMENSION),
        ],
        metrics=[Metric(name=metric_name)],
        limit=100_000,
    )

    logger.info(
        "Running GA4 report metric=%s property=%s range=%s..%s",
        metric_name,
        property_id,
        start_date,
        end_date,
    )
    response = client.run_report(request)
    return response, property_id


def run_report_query(
    *,
    dimensions: list[str],
    metrics: list[str],
    start_date: str,
    end_date: str,
) -> tuple[RunReportResponse, str]:
    """Generic GA4 Data API runReport (same style as google-analytics-mcp run_report)."""
    client, property_id = get_ga4_client()

    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=[Dimension(name=name) for name in dimensions],
        metrics=[Metric(name=name) for name in metrics],
        limit=100_000,
    )
    logger.info(
        "Running GA4 report dims=%s metrics=%s property=%s range=%s..%s",
        dimensions,
        metrics,
        property_id,
        start_date,
        end_date,
    )
    response = client.run_report(request)
    return response, property_id


def format_ga4_date(raw: str) -> str:
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"
    return raw


def normalize_channel(raw: str | None) -> str:
    if raw is None or raw.strip() == "":
        return "(not set)"
    return raw


def parse_dimension_metric_rows(
    response: RunReportResponse,
    *,
    dimension_keys: list[str],
    metric_keys: list[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in response.rows:
        item: dict[str, Any] = {}
        for index, key in enumerate(dimension_keys):
            raw = row.dimension_values[index].value
            if key == "date":
                item[key] = format_ga4_date(raw)
            elif key == "event_name":
                item[key] = raw or "(not set)"
            else:
                item[key] = raw
        for index, key in enumerate(metric_keys):
            item[key] = row.metric_values[index].value
        rows.append(item)
    return rows


def parse_channel_metric_rows(
    response: RunReportResponse,
    *,
    value_key: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in response.rows:
        date_raw = row.dimension_values[0].value
        channel_raw = row.dimension_values[1].value
        metric_raw = row.metric_values[0].value
        rows.append(
            {
                "date": format_ga4_date(date_raw),
                "channel": normalize_channel(channel_raw),
                value_key: metric_raw,
            }
        )
    return rows


def extract_currency(response: RunReportResponse) -> str | None:
    metadata = response.metadata
    if metadata and metadata.currency_code:
        return metadata.currency_code
    return None