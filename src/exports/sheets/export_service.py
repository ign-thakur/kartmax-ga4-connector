from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.api.schemas import SourceReportResponse
from src.api.service import fetch_gmv_report_for_api, fetch_sessions_report_for_api
from src.exports.sheets.client import (
    TAB_HEADERS,
    assert_tab_and_headers,
    read_tab_values,
    write_tab_values,
)
from src.exports.sheets.constants import (
    REPORT_TYPE_TO_TAB,
    SPREADSHEET_URL_TEMPLATE,
)
from src.exports.sheets.upsert import upsert_data_rows
from src.reports.gmv_by_channel import REPORT_TYPE as GMV_REPORT_TYPE
from src.reports.sessions_by_channel import REPORT_TYPE as SESSIONS_REPORT_TYPE

_SUPPORTED = frozenset({GMV_REPORT_TYPE, SESSIONS_REPORT_TYPE})


def validate_report_types(report_types: list[str]) -> list[str]:
    cleaned: list[str] = []
    for raw in report_types:
        rt = raw.strip()
        if not rt:
            continue
        if rt not in _SUPPORTED:
            raise ValueError(
                f"Unsupported report_type {rt!r}. "
                f"Use {GMV_REPORT_TYPE!r} or {SESSIONS_REPORT_TYPE!r}."
            )
        cleaned.append(rt)
    if not cleaned:
        raise ValueError("report_types must include at least one exportable report.")
    return list(dict.fromkeys(cleaned))


def _utc_synced_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _gmv_sheet_rows(
    report: SourceReportResponse,
    *,
    synced_at: str,
) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for item in report.data:
        if not isinstance(item, dict):
            continue
        rows.append(
            [
                item["date"],
                report.property_id,
                item["source"],
                item["gmv"],
                report.currency or "",
                report.start_date,
                report.end_date,
                synced_at,
            ]
        )
    return rows


def _sessions_sheet_rows(
    report: SourceReportResponse,
    *,
    synced_at: str,
) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for item in report.data:
        if not isinstance(item, dict):
            continue
        rows.append(
            [
                item["date"],
                report.property_id,
                item["source"],
                item["sessions"],
                report.start_date,
                report.end_date,
                synced_at,
            ]
        )
    return rows


def _export_one_tab(
    *,
    spreadsheet_id: str,
    tab_name: str,
    incoming_rows: list[list[Any]],
) -> dict[str, Any]:
    assert_tab_and_headers(
        spreadsheet_id=spreadsheet_id,
        tab_name=tab_name,
        expected_headers=TAB_HEADERS[tab_name],
    )
    existing = read_tab_values(spreadsheet_id, tab_name)
    header = existing[0]
    data_rows = existing[1:] if len(existing) > 1 else []
    merged, updated, inserted = upsert_data_rows(data_rows, incoming_rows)
    write_tab_values(spreadsheet_id, tab_name, [header, *merged])
    return {
        "tab": tab_name,
        "rows_exported": len(incoming_rows),
        "rows_updated": updated,
        "rows_inserted": inserted,
        "rows_total": len(merged),
    }


def export_reports_to_google_sheets(
    *,
    property_id: str,
    report_types: list[str],
    start_date: str,
    end_date: str,
    spreadsheet_id: str,
) -> dict[str, Any]:
    types = validate_report_types(report_types)
    synced_at = _utc_synced_at()
    results: list[dict[str, Any]] = []

    for report_type in types:
        tab = REPORT_TYPE_TO_TAB[report_type]
        if report_type == GMV_REPORT_TYPE:
            report = fetch_gmv_report_for_api(
                property_id=property_id,
                start_date=start_date,
                end_date=end_date,
            )
            incoming = _gmv_sheet_rows(report, synced_at=synced_at)
        else:
            report = fetch_sessions_report_for_api(
                property_id=property_id,
                start_date=start_date,
                end_date=end_date,
            )
            incoming = _sessions_sheet_rows(report, synced_at=synced_at)

        results.append(
            {
                "report_type": report_type,
                **_export_one_tab(
                    spreadsheet_id=spreadsheet_id,
                    tab_name=tab,
                    incoming_rows=incoming,
                ),
            }
        )

    return {
        "success": True,
        "spreadsheet_id": spreadsheet_id,
        "spreadsheet_url": SPREADSHEET_URL_TEMPLATE.format(spreadsheet_id=spreadsheet_id),
        "property_id": property_id,
        "start_date": start_date,
        "end_date": end_date,
        "synced_at": synced_at,
        "reports": results,
    }