import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.clients.analytics_client import parse_source_metric_rows_from_dict
from src.config.dates import ResolvedDateRange
from src.mcp.run_report_adapter import (
    McpRunReportError,
    build_run_report_arguments,
    run_report_via_mcp,
)


def test_build_run_report_arguments():
    date_range = ResolvedDateRange(
        start_date="2026-11-01",
        end_date="2026-11-07",
        label_start="2026-11-01",
        label_end="2026-11-07",
    )
    args = build_run_report_arguments(
        metric_name="grossPurchaseRevenue",
        date_range=date_range,
        property_id="123",
    )
    assert args["property_id"] == "123"
    assert args["dimensions"] == ["date", "sessionSource"]
    assert args["metrics"] == ["grossPurchaseRevenue"]
    assert args["date_ranges"][0]["start_date"] == "2026-11-01"


def test_parse_source_metric_rows_from_dict_uses_dimension_headers_order():
    payload = {
        "dimension_headers": [{"name": "sessionSource"}, {"name": "date"}],
        "metric_headers": [{"name": "sessions"}],
        "rows": [
            {
                "dimension_values": [{"value": "duckduckgo"}, {"value": "20261118"}],
                "metric_values": [{"value": "4"}],
            }
        ],
    }
    rows = parse_source_metric_rows_from_dict(payload, value_key="sessions")
    assert rows == [
        {"date": "2026-11-18", "source": "duckduckgo", "sessions": "4"},
    ]


def test_parse_source_metric_rows_from_dict_preserves_raw_source():
    payload = {
        "rows": [
            {
                "dimension_values": [{"value": "20261118"}, {"value": "google"}],
                "metric_values": [{"value": "99"}],
            },
            {
                "dimension_values": [{"value": "20261118"}, {"value": "(direct)"}],
                "metric_values": [{"value": "1"}],
            },
        ]
    }
    rows = parse_source_metric_rows_from_dict(payload, value_key="sessions")
    assert rows[0] == {"date": "2026-11-18", "source": "google", "sessions": "99"}
    assert rows[1]["source"] == "(direct)"


@patch("src.mcp.run_report_adapter.call_mcp_tool", new_callable=AsyncMock)
def test_run_report_via_mcp_success(mock_call):
    ga4_payload = {
        "rows": [
            {
                "dimension_values": [{"value": "20261118"}, {"value": "facebook.com"}],
                "metric_values": [{"value": "10"}],
            }
        ],
        "metadata": {"currency_code": "INR"},
    }
    mock_call.return_value = SimpleNamespace(
        is_error=False,
        content=[SimpleNamespace(text=json.dumps(ga4_payload))],
    )
    date_range = ResolvedDateRange(
        start_date="yesterday",
        end_date="yesterday",
        label_start="2026-11-18",
        label_end="2026-11-18",
    )
    property_id, data, currency = run_report_via_mcp(
        metric_name="sessions",
        date_range=date_range,
        value_key="sessions",
        property_id="352673114",
    )
    assert property_id == "352673114"
    assert currency == "INR"
    assert data[0]["source"] == "facebook.com"
    mock_call.assert_awaited_once()
    assert mock_call.await_args.kwargs.get("authenticated") is True


@patch("src.mcp.run_report_adapter.call_mcp_tool", new_callable=AsyncMock)
def test_run_report_via_mcp_tool_error(mock_call):
    mock_call.return_value = SimpleNamespace(
        is_error=True,
        content=[SimpleNamespace(text=json.dumps({"error": "Missing OAuth access token"}))],
    )
    date_range = ResolvedDateRange(
        start_date="yesterday",
        end_date="yesterday",
        label_start="2026-11-18",
        label_end="2026-11-18",
    )
    with pytest.raises(McpRunReportError, match="OAuth"):
        run_report_via_mcp(
            metric_name="sessions",
            date_range=date_range,
            value_key="sessions",
            property_id="352673114",
        )