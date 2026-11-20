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

SOURCE_DIMENSION = "sessionSource"
DATE_DIMENSION = "date"
EVENT_DIMENSION = "eventName"

EVENT_SUMMARY_METRICS = [
    "sessions",
    "eventCount",
    "totalUsers",
    "eventCountPerUser",
    "totalRevenue",
]


def run_source_report(
    *,
    metric_name: str,
    start_date: str,
    end_date: str,
) -> tuple[RunReportResponse, str]:
    """Direct Data API (used for validation tests; production reports use MCP)."""
    return run_report_query(
        dimensions=[DATE_DIMENSION, SOURCE_DIMENSION],
        metrics=[metric_name],
        start_date=start_date,
        end_date=end_date,
    )


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


def normalize_source(raw: str | None) -> str:
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


def parse_source_metric_rows(
    response: RunReportResponse,
    *,
    value_key: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in response.rows:
        date_raw = row.dimension_values[0].value
        source_raw = row.dimension_values[1].value
        metric_raw = row.metric_values[0].value
        rows.append(
            {
                "date": format_ga4_date(date_raw),
                "source": normalize_source(source_raw),
                value_key: metric_raw,
            }
        )
    return rows


def _metric_value_from_dict(entry: Any) -> str | None:
    if isinstance(entry, dict):
        return entry.get("value")
    return getattr(entry, "value", None)


def _header_names(headers: Any) -> list[str]:
    if not isinstance(headers, list):
        return []
    names: list[str] = []
    for header in headers:
        if isinstance(header, dict):
            name = header.get("name")
        else:
            name = getattr(header, "name", None)
        if name:
            names.append(str(name))
    return names


def _dimension_value_indices(dimension_headers: list[str]) -> tuple[int, int]:
    """Resolve date and sessionSource column indexes from GA4 header metadata."""
    try:
        date_idx = dimension_headers.index(DATE_DIMENSION)
        source_idx = dimension_headers.index(SOURCE_DIMENSION)
    except ValueError:
        date_idx, source_idx = 0, 1
    return date_idx, source_idx


def parse_source_metric_rows_from_dict(
    payload: dict[str, Any],
    *,
    value_key: str,
) -> list[dict[str, Any]]:
    """Parse GA4 runReport dict (MCP / proto_to_dict) into source rows."""
    dimension_headers = _header_names(
        payload.get("dimension_headers") or payload.get("dimensionHeaders")
    )
    date_idx, source_idx = _dimension_value_indices(dimension_headers)
    metric_headers = _header_names(
        payload.get("metric_headers") or payload.get("metricHeaders")
    )
    metric_idx = 0
    if metric_headers:
        ga4_metric_names = {
            "gmv": "grossPurchaseRevenue",
            "sessions": "sessions",
        }
        ga4_name = ga4_metric_names.get(value_key, value_key)
        if ga4_name in metric_headers:
            metric_idx = metric_headers.index(ga4_name)

    raw_rows = payload.get("rows") or []
    rows: list[dict[str, Any]] = []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        dim_vals = row.get("dimension_values") or row.get("dimensionValues") or []
        metric_vals = row.get("metric_values") or row.get("metricValues") or []
        if len(dim_vals) <= max(date_idx, source_idx) or len(metric_vals) <= metric_idx:
            continue
        date_raw = _metric_value_from_dict(dim_vals[date_idx]) or ""
        source_raw = _metric_value_from_dict(dim_vals[source_idx])
        metric_raw = _metric_value_from_dict(metric_vals[metric_idx])
        if metric_raw is None:
            continue
        rows.append(
            {
                "date": format_ga4_date(str(date_raw)),
                "source": normalize_source(source_raw),
                value_key: str(metric_raw),
            }
        )
    return rows


def extract_currency(response: RunReportResponse) -> str | None:
    metadata = response.metadata
    if metadata and metadata.currency_code:
        return metadata.currency_code
    return None


def extract_currency_from_dict(payload: dict[str, Any]) -> str | None:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        return None
    code = metadata.get("currency_code") or metadata.get("currencyCode")
    if code:
        return str(code)
    return None