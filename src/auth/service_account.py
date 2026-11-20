"""Shared Google service account credentials (GA4, Sheets, etc.)."""

from __future__ import annotations

from google.oauth2 import service_account

from src.config.settings import get_credentials_path

_SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"


def load_service_account_credentials(
    *,
    scopes: list[str],
) -> service_account.Credentials:
    return service_account.Credentials.from_service_account_file(
        str(get_credentials_path()),
        scopes=scopes,
    )


def sheets_credentials() -> service_account.Credentials:
    return load_service_account_credentials(scopes=[_SHEETS_SCOPE])