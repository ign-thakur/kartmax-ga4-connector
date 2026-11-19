from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from src.config.dates import resolve_date_range


@patch("src.config.dates.get_reporting_timezone", return_value="UTC")
def test_resolve_custom_iso_range(_mock_tz):
    result = resolve_date_range("2026-11-01", "2026-11-17")
    assert result.start_date == "2026-11-01"
    assert result.end_date == "2026-11-17"
    assert result.label_start == "2026-11-01"
    assert result.label_end == "2026-11-17"


@patch("src.config.dates.get_reporting_timezone", return_value="UTC")
def test_resolve_yesterday_preset(_mock_tz):
    result = resolve_date_range(None, None, preset="yesterday")
    assert result.start_date == "yesterday"
    assert result.end_date == "yesterday"


@patch("src.config.dates._today_in_property_tz")
def test_resolve_last_7_days_preset(mock_today):
    mock_today.return_value = datetime(2026, 11, 17, tzinfo=timezone.utc)
    result = resolve_date_range(None, None, preset="last-7-days")
    assert result.label_start == "2026-11-10"
    assert result.label_end == "2026-11-16"


def test_invalid_range_order():
    with pytest.raises(ValueError, match="start_date must be on or before"):
        resolve_date_range("2026-11-17", "2026-11-01")