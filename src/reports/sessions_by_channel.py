import logging

from src.config.dates import ResolvedDateRange
from src.mcp.report_queries import SESSIONS_METRIC
from src.mcp.run_report_adapter import McpRunReportError, run_report_via_mcp
from src.reports.output import (
    build_report_payload,
    validate_report_rows,
    write_report_json,
)

logger = logging.getLogger(__name__)

REPORT_TYPE = "sessions_by_source"
METRIC_NAME = SESSIONS_METRIC
METRIC_KEY = "sessions"
FILENAME_STEM = "sessions_by_source"


def fetch_sessions_by_source(
    date_range: ResolvedDateRange,
    *,
    property_id: str | None = None,
    allow_empty: bool = False,
) -> dict:
    try:
        resolved_id, data, _currency = run_report_via_mcp(
            metric_name=METRIC_NAME,
            date_range=date_range,
            value_key=METRIC_KEY,
            property_id=property_id,
        )
    except McpRunReportError:
        raise

    if data or not allow_empty:
        validate_report_rows(
            data,
            metric_key=METRIC_KEY,
            expect_currency=False,
            currency=None,
        )

    payload = build_report_payload(
        property_id=resolved_id,
        report_type=REPORT_TYPE,
        start_date=date_range.label_start,
        end_date=date_range.label_end,
        data=data,
    )
    logger.info("Sessions by source: %s rows", len(data))
    return payload


def run_and_save_sessions_by_source(date_range: ResolvedDateRange):
    payload = fetch_sessions_by_source(date_range)
    path = write_report_json(payload, FILENAME_STEM)
    return payload, path


fetch_sessions_by_channel = fetch_sessions_by_source
run_and_save_sessions_by_channel = run_and_save_sessions_by_source