import json
import time
from types import SimpleNamespace
from unittest.mock import patch

import jwt
import pytest
from fastapi.testclient import TestClient

from src.dashboard.app import app

API_KEY = "test-api-key-secret"
JWT_SECRET = "test-jwt-signing-secret-minimum-32-chars"
CLIENT_ID = "kartmax-backend"
CLIENT_SECRET = "test-client-secret-value"
PROPERTY_ID = "352673114"

CLIENTS_JSON = json.dumps(
    [
        {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "property_ids": [PROPERTY_ID],
            "scopes": ["reports:gmv", "reports:sessions", "health:read"],
        },
        {
            "client_id": "sessions-only",
            "client_secret": "sessions-only-secret-value",
            "property_ids": [PROPERTY_ID],
            "scopes": ["reports:sessions", "health:read"],
        },
    ]
)

GMV_PAYLOAD = {
    "property_id": PROPERTY_ID,
    "report_type": "gmv_by_source",
    "start_date": "2026-11-18",
    "end_date": "2026-11-18",
    "currency": "INR",
    "data": [{"date": "2026-11-18", "source": "google", "gmv": "100"}],
}

SESSIONS_PAYLOAD = {
    "property_id": PROPERTY_ID,
    "report_type": "sessions_by_source",
    "start_date": "2026-11-18",
    "end_date": "2026-11-18",
    "data": [{"date": "2026-11-18", "source": "google", "sessions": "10"}],
}


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


def _issue_token(client: TestClient, *, client_id=CLIENT_ID, client_secret=CLIENT_SECRET):
    return client.post(
        "/api/v1/auth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )


def test_token_issue_success(client):
    response = _issue_token(client)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == 30 * 60
    assert "reports:gmv" in body["scope"]
    claims = jwt.decode(
        body["access_token"],
        JWT_SECRET,
        algorithms=["HS256"],
        audience="kartmax-backend",
        issuer="kartmax-ga4-connector",
    )
    assert claims["client_id"] == CLIENT_ID
    assert PROPERTY_ID in claims["properties"]


def test_token_issue_invalid_credentials(client):
    response = _issue_token(client, client_secret="wrong-secret")
    assert response.status_code == 401


def test_bearer_gmv_report_success(client):
    token = _issue_token(client).json()["access_token"]
    with patch("src.api.service.fetch_gmv_by_source", return_value=GMV_PAYLOAD):
        response = client.get(
            "/api/v1/reports/gmv-by-source",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "property_id": PROPERTY_ID,
                "start_date": "2026-11-18",
                "end_date": "2026-11-18",
            },
        )
    assert response.status_code == 200


@patch("src.api.service.run_mcp_connectivity_check")
def test_bearer_health_success(mock_health, client):
    mock_health.return_value = SimpleNamespace(
        connected=True,
        run_report_available=True,
        error_message=None,
        ok=True,
    )
    token = _issue_token(client).json()["access_token"]
    response = client.get(
        "/api/v1/health",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_expired_token_rejected(client):
    now = int(time.time())
    payload = {
        "iss": "kartmax-ga4-connector",
        "aud": "kartmax-backend",
        "sub": CLIENT_ID,
        "client_id": CLIENT_ID,
        "iat": now - 4000,
        "nbf": now - 4000,
        "exp": now - 60,
        "scope": "reports:gmv reports:sessions health:read",
        "properties": [PROPERTY_ID],
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    with patch("src.api.service.fetch_gmv_by_source", return_value=GMV_PAYLOAD):
        response = client.get(
            "/api/v1/reports/gmv-by-source",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "property_id": PROPERTY_ID,
                "start_date": "2026-11-18",
                "end_date": "2026-11-18",
            },
        )
    assert response.status_code == 401


def test_invalid_signature_rejected(client):
    token = _issue_token(client).json()["access_token"]
    parts = token.split(".")
    assert len(parts) == 3
    tampered = ".".join([parts[0], parts[1], "invalidsignature"])
    response = client.get(
        "/api/v1/reports/sessions-by-source",
        headers={"Authorization": f"Bearer {tampered}"},
        params={
            "property_id": PROPERTY_ID,
            "start_date": "2026-11-18",
            "end_date": "2026-11-18",
        },
    )
    assert response.status_code == 401


def test_missing_token_rejected(client):
    response = client.get(
        "/api/v1/reports/gmv-by-source",
        params={
            "property_id": PROPERTY_ID,
            "start_date": "2026-11-18",
            "end_date": "2026-11-18",
        },
    )
    assert response.status_code == 401


def test_insufficient_scope_rejected(client):
    token = _issue_token(
        client,
        client_id="sessions-only",
        client_secret="sessions-only-secret-value",
    ).json()["access_token"]
    with patch("src.api.service.fetch_gmv_by_source", return_value=GMV_PAYLOAD):
        response = client.get(
            "/api/v1/reports/gmv-by-source",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "property_id": PROPERTY_ID,
                "start_date": "2026-11-18",
                "end_date": "2026-11-18",
            },
        )
    assert response.status_code == 403


def test_unauthorized_property_rejected(client):
    token = _issue_token(client).json()["access_token"]
    with patch("src.api.service.fetch_sessions_by_source", return_value=SESSIONS_PAYLOAD):
        response = client.get(
            "/api/v1/reports/sessions-by-source",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "property_id": "999888777",
                "start_date": "2026-11-18",
                "end_date": "2026-11-18",
            },
        )
    assert response.status_code == 403


def test_legacy_api_key_still_works(client):
    with patch("src.api.service.fetch_sessions_by_source", return_value=SESSIONS_PAYLOAD):
        response = client.get(
            "/api/v1/reports/sessions-by-source",
            headers={"X-API-Key": API_KEY},
            params={
                "property_id": "999888777",
                "start_date": "2026-11-18",
                "end_date": "2026-11-18",
            },
        )
    assert response.status_code == 200