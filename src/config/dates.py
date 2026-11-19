import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.config.settings import get_reporting_timezone


def _zoneinfo(name: str):
    if name.upper() == "UTC":
        return timezone.utc
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        raise ValueError(
            f"Unknown timezone '{name}'. Install the 'tzdata' package on Windows "
            "or set GA4_REPORTING_TIMEZONE to a valid IANA name."
        ) from None

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

PRESET_ALIASES = {
    "yesterday": "yesterday",
    "last-7-days": "last_7_days",
    "last_7_days": "last_7_days",
    "last-30-days": "last_30_days",
    "last_30_days": "last_30_days",
    "this-month": "this_month",
    "this_month": "this_month",
}


@dataclass(frozen=True)
class ResolvedDateRange:
    start_date: str
    end_date: str
    label_start: str
    label_end: str


def _today_in_property_tz() -> datetime:
    tz = _zoneinfo(get_reporting_timezone())
    return datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)


def _format_iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _resolve_single_bound(value: str, *, role: str) -> tuple[str, str]:
    """
    Return (ga4_api_date, display_label).
    GA4 accepts YYYY-MM-DD and relative strings like yesterday, 7daysAgo, today.
    """
    normalized = value.strip().lower()
    if normalized in PRESET_ALIASES:
        preset = PRESET_ALIASES[normalized]
        return _preset_to_ga4_range(preset, role)

    if ISO_DATE.match(value.strip()):
        iso = value.strip()
        return iso, iso

    ga4_relative = {
        "yesterday": ("yesterday", "yesterday"),
        "today": ("today", "today"),
    }
    if normalized in ga4_relative:
        api_val, label = ga4_relative[normalized]
        return api_val, label

    raise ValueError(
        f"Invalid {role} date '{value}'. Use YYYY-MM-DD or a preset "
        "(yesterday, last-7-days, last-30-days, this-month)."
    )


def _preset_to_ga4_range(preset: str, role: str) -> tuple[str, str]:
    today = _today_in_property_tz()

    if preset == "yesterday":
        day = today - timedelta(days=1)
        iso = _format_iso(day)
        if role == "start":
            return "yesterday", iso
        return "yesterday", iso

    if preset == "last_7_days":
        start = today - timedelta(days=7)
        end = today - timedelta(days=1)
        if role == "start":
            return _format_iso(start), _format_iso(start)
        return _format_iso(end), _format_iso(end)

    if preset == "last_30_days":
        start = today - timedelta(days=30)
        end = today - timedelta(days=1)
        if role == "start":
            return _format_iso(start), _format_iso(start)
        return _format_iso(end), _format_iso(end)

    if preset == "this_month":
        start = today.replace(day=1)
        end = today - timedelta(days=1)
        if end < start:
            end = start
        if role == "start":
            return _format_iso(start), _format_iso(start)
        return _format_iso(end), _format_iso(end)

    raise ValueError(f"Unknown preset: {preset}")


def resolve_date_range(
    start_date: str | None,
    end_date: str | None,
    preset: str | None = None,
) -> ResolvedDateRange:
    if preset:
        key = PRESET_ALIASES.get(preset.strip().lower())
        if not key:
            raise ValueError(f"Unknown preset '{preset}'.")
        if key == "yesterday":
            return ResolvedDateRange(
                start_date="yesterday",
                end_date="yesterday",
                label_start=_preset_label_end(key)[0],
                label_end=_preset_label_end(key)[1],
            )
        if key == "last_7_days":
            today = _today_in_property_tz()
            start = _format_iso(today - timedelta(days=7))
            end = _format_iso(today - timedelta(days=1))
            return ResolvedDateRange(start, end, start, end)
        if key == "last_30_days":
            today = _today_in_property_tz()
            start = _format_iso(today - timedelta(days=30))
            end = _format_iso(today - timedelta(days=1))
            return ResolvedDateRange(start, end, start, end)
        if key == "this_month":
            today = _today_in_property_tz()
            start = _format_iso(today.replace(day=1))
            end = _format_iso(today - timedelta(days=1))
            if end < start:
                end = start
            return ResolvedDateRange(start, end, start, end)

    if not start_date or not end_date:
        raise ValueError("Provide --start-date and --end-date, or use --preset.")

    start_api, label_start = _resolve_single_bound(start_date, role="start")
    end_api, label_end = _resolve_single_bound(end_date, role="end")

    if ISO_DATE.match(label_start) and ISO_DATE.match(label_end):
        if label_start > label_end:
            raise ValueError("start_date must be on or before end_date.")

    return ResolvedDateRange(
        start_date=start_api,
        end_date=end_api,
        label_start=label_start,
        label_end=label_end,
    )


def _preset_label_end(key: str) -> tuple[str, str]:
    today = _today_in_property_tz()
    if key == "yesterday":
        iso = _format_iso(today - timedelta(days=1))
        return iso, iso
    return "", ""