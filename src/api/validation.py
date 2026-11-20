"""Request validation for Backend REST APIs."""

from __future__ import annotations

import os
import re
from datetime import date, timedelta

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PROPERTY_ID = re.compile(r"^\d{1,12}$")

DEFAULT_MAX_RANGE_DAYS = 366


def get_max_report_range_days() -> int:
    raw = os.getenv("REPORT_MAX_RANGE_DAYS", str(DEFAULT_MAX_RANGE_DAYS)).strip()
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_RANGE_DAYS
    if value < 1:
        return DEFAULT_MAX_RANGE_DAYS
    return min(value, DEFAULT_MAX_RANGE_DAYS)


def validate_property_id(property_id: str) -> str:
    cleaned = property_id.strip()
    if not PROPERTY_ID.match(cleaned):
        raise ValueError(
            "property_id must be a numeric GA4 property ID (1–12 digits)."
        )
    return cleaned


def validate_report_date_range(start_date: str, end_date: str) -> tuple[str, str]:
    if not ISO_DATE.match(start_date) or not ISO_DATE.match(end_date):
        raise ValueError("start_date and end_date must be YYYY-MM-DD.")

    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError as exc:
        raise ValueError("start_date and end_date must be valid calendar dates.") from exc

    if start > end:
        raise ValueError("start_date must be on or before end_date.")

    max_days = get_max_report_range_days()
    if (end - start).days > max_days - 1:
        raise ValueError(
            f"Date range exceeds the maximum of {max_days} days "
            f"(configure REPORT_MAX_RANGE_DAYS)."
        )

    return start_date, end_date