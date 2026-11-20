"""Optional live Google Sheets export (requires credentials + shared spreadsheet)."""

import json
import os

import pytest
from fastapi.testclient import TestClient

from src.dashboard.app import app


def _require_live_spreadsheet_id() -> str:
    """Return test spreadsheet ID when live tests are enabled; skip or fail otherwise."""
    if os.getenv("RUN_SHEETS_LIVE_TESTS", "").strip().lower() not in ("1", "true", "yes"):
        pytest.skip("Set RUN_SHEETS_LIVE_TESTS=1 to run live Sheets export tests.")
    if not os.getenv("JWT_SIGNING_SECRET", "").strip():
        pytest.skip("JWT_SIGNING_SECRET required for live Sheets export tests.")
    sheet_id = os.getenv("GOOGLE_SHEETS_TEST_SPREADSHEET_ID", "").strip()
    if not sheet_id:
        pytest.fail(
            "RUN_SHEETS_LIVE_TESTS is enabled but GOOGLE_SHEETS_TEST_SPREADSHEET_ID is not set. "
            "Set it to a spreadsheet shared with the service account (Editor)."
        )
    return sheet_id


def test_live_export_to_shared_spreadsheet(monkeypatch):
    sheet_id = _require_live_spreadsheet_id()
    clients = os.getenv("KARTMAX_OAUTH_CLIENTS", "").strip()
    if not clients:
        pytest.skip("KARTMAX_OAUTH_CLIENTS required.")

    client = TestClient(app)
    token_resp = client.post(
        "/api/v1/auth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": json.loads(clients)[0]["client_id"],
            "client_secret": json.loads(clients)[0]["client_secret"],
        },
    )
    assert token_resp.status_code == 200
    token = token_resp.json()["access_token"]
    property_id = json.loads(clients)[0]["property_ids"][0]

    response = client.post(
        "/api/v1/exports/google-sheets",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "property_id": property_id,
            "report_types": ["sessions_by_source"],
            "start_date": "2026-11-18",
            "end_date": "2026-11-18",
            "spreadsheet_id": sheet_id,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reports"][0]["rows_exported"] >= 1