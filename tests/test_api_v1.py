import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.dashboard.app import create_app
from src.mcp.run_report_adapter import McpRunReportError

API_KEY = "test-api-key-secret"
HEADERS = {"X-API-Key": API_KEY}

GMV_PAYLOAD = {
    "property_id": "352673114",
    "report_type": "gmv_by_source",
    "start_date": "2026-11-18",
    "end_date": "2026-11-18",
    "currency": "INR",
    "data": [
        {"date": "2026-11-18", "source": "google", "gmv": "80655.000222"},
    ],
}

SESSIONS_PAYLOAD = {
    "property_id": "352673114",
    "report_type": "sessions_by_source",
    "start_date": "2026-11-18",
    "end_date": "2026-11-18",
    "data": [
        {"date": "2026-11-18", "source": "google", "sessions": "4094"},
    ],
}


@pytest.fixture
def client():
    """Fresh API app; legacy dashboard routes depend on ENABLE_DASHBOARD at create time."""
    return TestClient(create_app())


@pytest.fixture
def legacy_dashboard_client():
    """Legacy unauthenticated dashboard routes (dev-only profile)."""
    with patch("src.dashboard.app.is_dashboard_enabled", return_value=True):
        with patch("src.dashboard.app.is_ops_console_enabled", return_value=False):
            yield TestClient(create_app())


@pytest.fixture(autouse=True)
def api_key_env(monkeypatch):
    monkeypatch.setenv("KARTMAX_API_KEY", API_KEY)


def test_health_requires_api_key(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 401


@patch("src.api.service.run_mcp_connectivity_check")
def test_health_success(mock_health, client):
    mock_health.return_value = SimpleNamespace(
        connected=True,
        run_report_available=True,
        server_url="http://127.0.0.1:8000/mcp",
        error_message=None,
        ok=True,
    )
    response = client.get("/api/v1/health", headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mcp"]["run_report_available"] is True
    assert "server_url" not in body["mcp"]
    assert "server_url" not in json.dumps(body)


def test_sessions_api_rows_use_separate_source_and_metric_keys(client):
    payload = {
        **SESSIONS_PAYLOAD,
        "data": [
            {"date": "2026-11-18", "source": "duckduckgo", "sessions": "4"},
            {"date": "2026-11-18", "source": "(not set)", "sessions": "139"},
        ],
    }
    with patch("src.api.service.fetch_sessions_by_source", return_value=payload):
        response = client.get(
            "/api/v1/reports/sessions-by-source",
            headers=HEADERS,
            params={
                "property_id": "352673114",
                "start_date": "2026-11-18",
                "end_date": "2026-11-18",
            },
        )
    assert response.status_code == 200
    for row in response.json()["data"]:
        assert set(row.keys()) == {"date", "source", "sessions"}
        assert "sourcesessions" not in row
        assert row["source"] != "sourcesessions"


@patch("src.api.service.fetch_gmv_by_source", return_value=GMV_PAYLOAD)
def test_gmv_by_source_success(mock_fetch, client):
    response = client.get(
        "/api/v1/reports/gmv-by-source",
        headers=HEADERS,
        params={
            "property_id": "352673114",
            "start_date": "2026-11-18",
            "end_date": "2026-11-18",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["report_type"] == "gmv_by_source"
    assert body["currency"] == "INR"
    assert isinstance(body["data"][0]["gmv"], float)
    mock_fetch.assert_called_once()
    assert mock_fetch.call_args.kwargs["property_id"] == "352673114"


@patch("src.api.service.fetch_sessions_by_source", return_value=SESSIONS_PAYLOAD)
def test_sessions_by_source_success(mock_fetch, client):
    response = client.get(
        "/api/v1/reports/sessions-by-source",
        headers=HEADERS,
        params={
            "property_id": "999888777",
            "start_date": "2026-11-01",
            "end_date": "2026-11-18",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["report_type"] == "sessions_by_source"
    assert isinstance(body["data"][0]["sessions"], float)
    assert mock_fetch.call_args.kwargs["property_id"] == "999888777"


def test_missing_api_key(client):
    response = client.get(
        "/api/v1/reports/gmv-by-source",
        params={
            "property_id": "352673114",
            "start_date": "2026-11-18",
            "end_date": "2026-11-18",
        },
    )
    assert response.status_code == 401


def test_invalid_property_id(client):
    response = client.get(
        "/api/v1/reports/gmv-by-source",
        headers=HEADERS,
        params={
            "property_id": "not-a-number",
            "start_date": "2026-11-18",
            "end_date": "2026-11-18",
        },
    )
    assert response.status_code == 422


def test_start_after_end(client):
    response = client.get(
        "/api/v1/reports/sessions-by-source",
        headers=HEADERS,
        params={
            "property_id": "352673114",
            "start_date": "2026-11-20",
            "end_date": "2026-11-18",
        },
    )
    assert response.status_code == 422


def test_range_too_large(client, monkeypatch):
    monkeypatch.setenv("REPORT_MAX_RANGE_DAYS", "7")
    response = client.get(
        "/api/v1/reports/sessions-by-source",
        headers=HEADERS,
        params={
            "property_id": "352673114",
            "start_date": "2026-11-01",
            "end_date": "2026-11-18",
        },
    )
    assert response.status_code == 422


@patch("src.api.service.fetch_gmv_by_source", return_value={**GMV_PAYLOAD, "data": []})
def test_empty_gmv_results(mock_fetch, client):
    response = client.get(
        "/api/v1/reports/gmv-by-source",
        headers=HEADERS,
        params={
            "property_id": "352673114",
            "start_date": "2026-11-18",
            "end_date": "2026-11-18",
        },
    )
    assert response.status_code == 200
    assert response.json()["data"] == []


@patch(
    "src.api.service.fetch_gmv_by_source",
    side_effect=McpRunReportError("Failed to refresh Google access token"),
)
def test_mcp_auth_failure(mock_fetch, client):
    response = client.get(
        "/api/v1/reports/gmv-by-source",
        headers=HEADERS,
        params={
            "property_id": "352673114",
            "start_date": "2026-11-18",
            "end_date": "2026-11-18",
        },
    )
    assert response.status_code == 502


@patch(
    "src.api.service.fetch_sessions_by_source",
    side_effect=McpRunReportError(
        "MCP connection failed for http://127.0.0.1:8000/mcp: ConnectError"
    ),
)
def test_mcp_unavailable(mock_fetch, client):
    response = client.get(
        "/api/v1/reports/sessions-by-source",
        headers=HEADERS,
        params={
            "property_id": "352673114",
            "start_date": "2026-11-18",
            "end_date": "2026-11-18",
        },
    )
    assert response.status_code == 503


def test_dashboard_index_still_available(legacy_dashboard_client):
    response = legacy_dashboard_client.get("/")
    assert response.status_code == 200


@patch("src.dashboard.events_service.fetch_events_by_name")
def test_events_direct_api_still_used(mock_fetch, legacy_dashboard_client):
    mock_fetch.return_value = {
        "property_id": "352673114",
        "report_type": "events_by_name",
        "start_date": "2026-11-18",
        "end_date": "2026-11-18",
        "summary": [{"event_name": "purchase"}],
        "daily": [],
    }
    response = legacy_dashboard_client.get(
        "/api/events",
        params={
            "start_date": "2026-11-18",
            "end_date": "2026-11-18",
        },
    )
    assert response.status_code == 200
    mock_fetch.assert_called_once()