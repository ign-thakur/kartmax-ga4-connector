"""Compare MCP source reports to direct GA4 Data API (integration)."""

import os

import pytest

from src.clients.analytics_client import (
    extract_currency,
    parse_source_metric_rows,
    run_source_report,
)
from src.config.dates import ResolvedDateRange
from src.config.settings import get_property_id
from src.mcp.report_queries import GMV_METRIC, SESSIONS_METRIC
from src.mcp.run_report_adapter import run_report_via_mcp


def _sort_rows(rows: list[dict], metric_key: str) -> list[tuple]:
    return sorted(
        (r["date"], r["source"], r[metric_key]) for r in rows
    )


def _skip_unless_live() -> None:
    if os.getenv("RUN_GA4_LIVE_TESTS", "").strip().lower() not in ("1", "true", "yes"):
        pytest.skip("Set RUN_GA4_LIVE_TESTS=1 to run GA4 parity tests.")
    if not os.getenv("MCP_SERVER_URL", "").strip():
        pytest.skip("MCP_SERVER_URL required for MCP parity tests.")


@pytest.mark.parametrize("metric_name, metric_key", [
    (SESSIONS_METRIC, "sessions"),
    (GMV_METRIC, "gmv"),
])
def test_mcp_matches_direct_api_for_source_report(metric_name, metric_key):
    _skip_unless_live()
    date_range = ResolvedDateRange(
        start_date="yesterday",
        end_date="yesterday",
        label_start="yesterday",
        label_end="yesterday",
    )

    _, mcp_rows, mcp_currency = run_report_via_mcp(
        metric_name=metric_name,
        date_range=date_range,
        value_key=metric_key,
        property_id=get_property_id(),
    )
    assert mcp_rows, "MCP returned no rows for yesterday"

    direct_response, _ = run_source_report(
        metric_name=metric_name,
        start_date=date_range.start_date,
        end_date=date_range.end_date,
    )
    direct_rows = parse_source_metric_rows(direct_response, value_key=metric_key)
    assert direct_rows, "Direct API returned no rows for yesterday"

    assert _sort_rows(mcp_rows, metric_key) == _sort_rows(direct_rows, metric_key)

    if metric_key == "gmv":
        direct_currency = extract_currency(direct_response)
        assert mcp_currency == direct_currency