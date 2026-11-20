from __future__ import annotations

import re

from src.reports.gmv_by_channel import REPORT_TYPE as GMV_REPORT_TYPE
from src.reports.sessions_by_channel import REPORT_TYPE as SESSIONS_REPORT_TYPE

TAB_GMV = "GMV by Source"
TAB_SESSIONS = "Sessions by Source"

GMV_HEADERS = [
    "Date",
    "Property ID",
    "Source",
    "GMV",
    "Currency",
    "Report Start Date",
    "Report End Date",
    "Last Synced At",
]

SESSIONS_HEADERS = [
    "Date",
    "Property ID",
    "Source",
    "Sessions",
    "Report Start Date",
    "Report End Date",
    "Last Synced At",
]

REPORT_TYPE_TO_TAB: dict[str, str] = {
    GMV_REPORT_TYPE: TAB_GMV,
    SESSIONS_REPORT_TYPE: TAB_SESSIONS,
}

SPREADSHEET_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{10,128}$")

SPREADSHEET_URL_TEMPLATE = "https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"