from __future__ import annotations

from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.auth.service_account import sheets_credentials
from src.exports.sheets.constants import GMV_HEADERS, SESSIONS_HEADERS, TAB_GMV, TAB_SESSIONS
from src.exports.sheets.errors import (
    SheetsNotFoundError,
    SheetsPermissionError,
    SheetsTabError,
)

_sheets_service: Any | None = None


def get_sheets_service():
    global _sheets_service
    if _sheets_service is None:
        creds = sheets_credentials()
        _sheets_service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    return _sheets_service


def _translate_http_error(exc: HttpError, *, spreadsheet_id: str, tab_name: str) -> Exception:
    status = exc.resp.status if exc.resp else 0
    if status in (403, 401):
        return SheetsPermissionError(
            "Google Sheets API denied access. Share the spreadsheet with the "
            "service account email (Editor) and ensure the Sheets API is enabled."
        )
    if status == 404:
        return SheetsNotFoundError(f"Spreadsheet {spreadsheet_id!r} was not found.")
    if status == 400:
        return SheetsTabError(tab_name, f"Invalid Sheets request for tab {tab_name!r}: {exc}")
    return SheetsTabError(tab_name, f"Google Sheets API error ({status}): {exc}")


def list_sheet_titles(spreadsheet_id: str) -> list[str]:
    service = get_sheets_service()
    try:
        meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    except HttpError as exc:
        raise _translate_http_error(exc, spreadsheet_id=spreadsheet_id, tab_name="") from exc
    sheets = meta.get("sheets") or []
    return [
        str(s.get("properties", {}).get("title", ""))
        for s in sheets
        if s.get("properties", {}).get("title")
    ]


def read_tab_values(spreadsheet_id: str, tab_name: str) -> list[list[Any]]:
    service = get_sheets_service()
    range_name = f"'{tab_name}'"
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )
    except HttpError as exc:
        raise _translate_http_error(exc, spreadsheet_id=spreadsheet_id, tab_name=tab_name) from exc
    return list(result.get("values") or [])


def write_tab_values(
    spreadsheet_id: str,
    tab_name: str,
    values: list[list[Any]],
) -> None:
    if not values:
        return
    service = get_sheets_service()
    range_name = f"'{tab_name}'!A1"
    body = {"values": values}
    try:
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            body=body,
        ).execute()
    except HttpError as exc:
        raise _translate_http_error(exc, spreadsheet_id=spreadsheet_id, tab_name=tab_name) from exc


def assert_tab_and_headers(
    *,
    spreadsheet_id: str,
    tab_name: str,
    expected_headers: list[str],
) -> None:
    titles = list_sheet_titles(spreadsheet_id)
    if tab_name not in titles:
        raise SheetsTabError(
            tab_name,
            f"Worksheet tab {tab_name!r} does not exist. Create it manually; "
            "the connector does not auto-create tabs.",
        )
    rows = read_tab_values(spreadsheet_id, tab_name)
    if not rows:
        raise SheetsTabError(tab_name, f"Tab {tab_name!r} is empty (header row required).")
    header = [str(c).strip() for c in rows[0]]
    if header != expected_headers:
        raise SheetsTabError(
            tab_name,
            f"Tab {tab_name!r} headers do not match expected layout. "
            f"Expected {expected_headers!r}, got {header!r}.",
        )


TAB_HEADERS = {
    TAB_GMV: GMV_HEADERS,
    TAB_SESSIONS: SESSIONS_HEADERS,
}