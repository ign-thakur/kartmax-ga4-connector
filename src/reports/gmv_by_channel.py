import logging

from src.clients.analytics_client import (
    extract_currency,
    parse_channel_metric_rows,
    run_channel_report,
)
from src.config.dates import ResolvedDateRange
from src.reports.output import (
    build_report_payload,
    validate_report_rows,
    write_report_json,
)

logger = logging.getLogger(__name__)

REPORT_TYPE = "gmv_by_channel"
METRIC_NAME = "grossPurchaseRevenue"
METRIC_KEY = "gmv"
FILENAME_STEM = "gmv_by_channel"


def fetch_gmv_by_channel(date_range: ResolvedDateRange) -> dict:
    response, property_id = run_channel_report(
        metric_name=METRIC_NAME,
        start_date=date_range.start_date,
        end_date=date_range.end_date,
    )

    currency = extract_currency(response)
    data = parse_channel_metric_rows(response, value_key=METRIC_KEY)
    validate_report_rows(
        data,
        metric_key=METRIC_KEY,
        expect_currency=True,
        currency=currency,
    )

    payload = build_report_payload(
        property_id=property_id,
        report_type=REPORT_TYPE,
        start_date=date_range.label_start,
        end_date=date_range.label_end,
        currency=currency,
        data=data,
    )
    logger.info("GMV by channel: %s rows", len(data))
    return payload


def run_and_save_gmv_by_channel(date_range: ResolvedDateRange):
    payload = fetch_gmv_by_channel(date_range)
    path = write_report_json(payload, FILENAME_STEM)
    return payload, path