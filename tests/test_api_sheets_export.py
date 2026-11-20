import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.schemas import SourceReportResponse
from src.dashboard.app import app
from src.exports.sheets.constants import TAB_GMV
from src.exports.sheets.errors import SheetsTabError

API_KEY = "test-api-key-secret"
JWT_SECRET = "test-jwt-signing-secret-minimum-32-chars"
CLIENT_ID = "kartmax-backend"
CLIENT_SECRET = "test-client-secret-value"
SHEET_ID = "1Cr-Rt0LtjqguWTrGuxTxMfSSBQfjO--X6U12bIXzdeg"

CLIENTS_JSON = json.dumps(
    [
        {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "property_ids": ["352673114"],
            "scopes": ["reports:gmv", "reports:sessions", "health:read"],
        }
    ]
)

GMV_REPORT = SourceReportResponse.model_validate(
    {
        "report_type": "gmv_by_source",
        "property_id": "352673114",
        "start_date": "2026-11-18",
        "end_date": "2026-11-18",
        "currency": "INR",
        "data": [{"date": "2026-11-18", "source": "google", "gmv": 100.0}],
    }
)

SESSIONS_REPORT = SourceReportResponse.model_validate(
    {
        "report_type": "sessions_by_source",
        "property_id": "352673114",
        "start_date": "2026-11-18",
        "end_date": "2026-11-18",
        "data": [{"date": "2026-11-18", "source": "google", "sessions": 10.0}],
    }
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def auth_env(monkeypatch):
    monkeypatch.setenv("KARTMAX_API_KEY", API_KEY)
    monkeypatch.setenv("JWT_SIGNING_SECRET", JWT_SECRET)
    monkeypatch.setenv("JWT_ISSUER", "kartmax-ga4-connector")
    monkeypatch.setenv("JWT_AUDIENCE", "kartmax-backend")
    monkeypatch.setenv("KARTMAX_OAUTH_CLIENTS", CLIENTS_JSON)


def _token(client):
    response = client.post(
        "/api/v1/auth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
    )
    return response.json()["access_token"]


def _export_body(**overrides):
    body = {
        "property_id": "352673114",
        "report_types": ["gmv_by_source", "sessions_by_source"],
        "start_date": "2026-11-18",
        "end_date": "2026-11-18",
        "spreadsheet_id": SHEET_ID,
    }
    body.update(overrides)
    return body


@patch("src.exports.sheets.export_service.write_tab_values")
@patch("src.exports.sheets.export_service.read_tab_values")
@patch("src.exports.sheets.export_service.assert_tab_and_headers")
@patch(
    "src.exports.sheets.export_service.fetch_sessions_report_for_api",
    return_value=SESSIONS_REPORT,
)
@patch(
    "src.exports.sheets.export_service.fetch_gmv_report_for_api",
    return_value=GMV_REPORT,
)
def test_export_success(
    mock_gmv,
    mock_sessions,
    mock_headers,
    mock_read,
    mock_write,
    client,
):
    mock_read.side_effect = [
        [
            [
                "Date",
                "Property ID",
                "Source",
                "GMV",
                "Currency",
                "Report Start Date",
                "Report End Date",
                "Last Synced At",
            ]
        ],
        [
            [
                "Date",
                "Property ID",
                "Source",
                "Sessions",
                "Report Start Date",
                "Report End Date",
                "Last Synced At",
            ]
        ],
    ]
    token = _token(client)
    response = client.post(
        "/api/v1/exports/google-sheets",
        headers={"Authorization": f"Bearer {token}"},
        json=_export_body(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["spreadsheet_id"] == SHEET_ID
    assert "docs.google.com/spreadsheets" in body["spreadsheet_url"]
    assert len(body["reports"]) == 2
    assert body["reports"][0]["rows_exported"] == 1
    assert mock_write.call_count == 2


def test_export_requires_bearer(client):
    response = client.post(
        "/api/v1/exports/google-sheets",
        headers={"X-API-Key": API_KEY},
        json=_export_body(),
    )
    assert response.status_code == 401


def test_export_unauthorized_property(client):
    token = _token(client)
    response = client.post(
        "/api/v1/exports/google-sheets",
        headers={"Authorization": f"Bearer {token}"},
        json=_export_body(property_id="999888777"),
    )
    assert response.status_code == 403


@patch("src.exports.sheets.export_service.assert_tab_and_headers")
@patch(
    "src.exports.sheets.export_service.fetch_gmv_report_for_api",
    return_value=GMV_REPORT,
)
def test_export_missing_tab(mock_gmv, mock_headers, client):
    mock_headers.side_effect = SheetsTabError(TAB_GMV, "Tab missing")
    token = _token(client)
    response = client.post(
        "/api/v1/exports/google-sheets",
        headers={"Authorization": f"Bearer {token}"},
        json=_export_body(report_types=["gmv_by_source"]),
    )
    assert response.status_code == 422
    assert "Tab missing" in response.json()["detail"]


def test_gmv_sheet_rows_preserve_raw_sources():
    from src.exports.sheets.export_service import _gmv_sheet_rows

    report = SourceReportResponse.model_validate(
        {
            "report_type": "gmv_by_source",
            "property_id": "352673114",
            "start_date": "2026-11-01",
            "end_date": "2026-11-18",
            "currency": "INR",
            "data": [
                {"date": "2026-11-18", "source": "(not set)", "gmv": 1.0},
                {"date": "2026-11-18", "source": "m.facebook.com", "gmv": 2.5},
            ],
        }
    )
    rows = _gmv_sheet_rows(report, synced_at="2026-11-19T10:00:00+00:00")
    assert rows[0][2] == "(not set)"
    assert rows[1][2] == "m.facebook.com"
    assert rows[0][3] == 1.0


def test_sessions_sheet_rows_numeric_values():
    from src.exports.sheets.export_service import _sessions_sheet_rows

    report = SourceReportResponse.model_validate(
        {
            "report_type": "sessions_by_source",
            "property_id": "352673114",
            "start_date": "2026-11-18",
            "end_date": "2026-11-18",
            "data": [{"date": "2026-11-18", "source": "google", "sessions": 4094.0}],
        }
    )
    rows = _sessions_sheet_rows(report, synced_at="2026-11-19T10:00:00+00:00")
    assert rows[0][3] == 4094.0