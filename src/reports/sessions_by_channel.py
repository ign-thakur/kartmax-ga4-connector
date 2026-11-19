import logging

from src.clients.analytics_client import parse_channel_metric_rows, run_channel_report
from src.config.dates import ResolvedDateRange
from src.reports.output import (
    build_report_payload,
    validate_report_rows,
    write_report_json,
)

logger = logging.getLogger(__name__)

REPORT_TYPE = "sessions_by_channel"
METRIC_NAME = "sessions"
METRIC_KEY = "sessions"
FILENAME_STEM = "sessions_by_channel"


def fetch_sessions_by_channel(date_range: ResolvedDateRange) -> dict:
    response, property_id = run_channel_report(
        metric_name=METRIC_NAME,
        start_date=date_range.start_date,
        end_date=date_range.end_date,
    )

    data = parse_channel_metric_rows(response, value_key=METRIC_KEY)
    validate_report_rows(
        data,
        metric_key=METRIC_KEY,
        expect_currency=False,
        currency=None,
    )

    payload = build_report_payload(
        property_id=property_id,
        report_type=REPORT_TYPE,
        start_date=date_range.label_start,
        end_date=date_range.label_end,
        data=data,
    )
    logger.info("Sessions by channel: %s rows", len(data))
    return payload


def run_and_save_sessions_by_channel(date_range: ResolvedDateRange):
    payload = fetch_sessions_by_channel(date_range)
    path = write_report_json(payload, FILENAME_STEM)
    return payload, path