from src.clients.analytics_client import (
    format_ga4_date,
    normalize_source,
    parse_source_metric_rows,
    parse_source_metric_rows_from_dict,
)
from src.reports.output import build_report_payload, validate_report_rows


class _DimValue:
    def __init__(self, value):
        self.value = value


class _MetricValue:
    def __init__(self, value):
        self.value = value


class _Row:
    def __init__(self, date, source, metric):
        self.dimension_values = [_DimValue(date), _DimValue(source)]
        self.metric_values = [_MetricValue(metric)]


class _Response:
    def __init__(self, rows):
        self.rows = rows


def test_format_ga4_date():
    assert format_ga4_date("20261101") == "2026-11-01"


def test_normalize_source():
    assert normalize_source("") == "(not set)"
    assert normalize_source("google") == "google"
    assert normalize_source("(direct)") == "(direct)"


def test_parse_source_metric_rows_proto():
    response = _Response(
        [
            _Row("20261101", "google", "150000.5"),
            _Row("20261101", "", "10"),
        ]
    )
    rows = parse_source_metric_rows(response, value_key="gmv")
    assert rows[0]["date"] == "2026-11-01"
    assert rows[0]["source"] == "google"
    assert rows[0]["gmv"] == "150000.5"
    assert rows[1]["source"] == "(not set)"


def test_validate_report_rows_source():
    validate_report_rows(
        [{"date": "2026-11-01", "source": "bing", "sessions": "12"}],
        metric_key="sessions",
        expect_currency=False,
        currency=None,
    )


def test_build_report_payload_includes_currency():
    payload = build_report_payload(
        property_id="352673114",
        report_type="gmv_by_source",
        start_date="2026-11-01",
        end_date="2026-11-17",
        currency="INR",
        data=[],
    )
    assert payload["property_id"] == "352673114"
    assert payload["currency"] == "INR"
    assert payload["report_type"] == "gmv_by_source"
    assert "generated_at" in payload