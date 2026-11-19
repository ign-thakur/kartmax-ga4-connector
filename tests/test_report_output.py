from src.clients.analytics_client import (
    format_ga4_date,
    normalize_channel,
    parse_channel_metric_rows,
)
from src.reports.output import build_report_payload


class _DimValue:
    def __init__(self, value):
        self.value = value


class _MetricValue:
    def __init__(self, value):
        self.value = value


class _Row:
    def __init__(self, date, channel, metric):
        self.dimension_values = [_DimValue(date), _DimValue(channel)]
        self.metric_values = [_MetricValue(metric)]


class _Response:
    def __init__(self, rows):
        self.rows = rows


def test_format_ga4_date():
    assert format_ga4_date("20261101") == "2026-11-01"


def test_normalize_channel():
    assert normalize_channel("") == "(not set)"
    assert normalize_channel("Direct") == "Direct"


def test_parse_channel_metric_rows():
    response = _Response(
        [
            _Row("20261101", "Organic Search", "150000.5"),
            _Row("20261101", "", "10"),
        ]
    )
    rows = parse_channel_metric_rows(response, value_key="gmv")
    assert rows[0]["date"] == "2026-11-01"
    assert rows[0]["channel"] == "Organic Search"
    assert rows[0]["gmv"] == "150000.5"
    assert rows[1]["channel"] == "(not set)"


def test_build_report_payload_includes_currency():
    payload = build_report_payload(
        property_id="352673114",
        report_type="gmv_by_channel",
        start_date="2026-11-01",
        end_date="2026-11-17",
        currency="INR",
        data=[],
    )
    assert payload["property_id"] == "352673114"
    assert payload["currency"] == "INR"
    assert "generated_at" in payload