from __future__ import annotations


class SheetsExportError(Exception):
    """Base error for Google Sheets export."""


class SheetsPermissionError(SheetsExportError):
    """Spreadsheet not accessible with service account."""


class SheetsNotFoundError(SheetsExportError):
    """Spreadsheet or tab not found."""


class SheetsTabError(SheetsExportError):
    """Tab missing or header mismatch."""

    def __init__(self, tab_name: str, detail: str) -> None:
        self.tab_name = tab_name
        super().__init__(detail)