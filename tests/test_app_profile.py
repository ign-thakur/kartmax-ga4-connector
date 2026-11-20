from unittest.mock import patch

from fastapi.testclient import TestClient

from src.config.app_profile import is_ops_console_enabled
from src.dashboard.app import create_app


def test_production_profile_hides_legacy_routes():
    with patch("src.dashboard.app.is_dashboard_enabled", return_value=False):
        with patch("src.dashboard.app.is_ops_console_enabled", return_value=False):
            prod = create_app()
    client = TestClient(prod)
    assert client.get("/").status_code == 404
    assert client.get("/api/dashboard").status_code == 404
    assert client.get("/api/events").status_code == 404
    assert client.get("/api/reports").status_code == 404


def test_development_profile_serves_dashboard():
    with patch("src.dashboard.app.is_dashboard_enabled", return_value=True):
        with patch("src.dashboard.app.is_ops_console_enabled", return_value=False):
            dev = create_app()
    client = TestClient(dev)
    assert client.get("/").status_code == 200


def test_v1_api_available_in_production_profile():
    with patch("src.dashboard.app.is_dashboard_enabled", return_value=False):
        with patch("src.dashboard.app.is_ops_console_enabled", return_value=False):
            prod = create_app()
    client = TestClient(prod)
    assert client.get("/api/v1/health").status_code == 401


def test_ops_console_hidden_by_default():
    with patch("src.dashboard.app.is_ops_console_enabled", return_value=False):
        app = create_app()
    client = TestClient(app)
    assert client.get("/ops").status_code == 404


def test_ops_console_served_when_enabled():
    with patch("src.dashboard.app.is_dashboard_enabled", return_value=False):
        with patch("src.dashboard.app.is_ops_console_enabled", return_value=True):
            app = create_app()
    client = TestClient(app)
    assert client.get("/ops").status_code == 200
    assert "Ops Console" in client.get("/ops").text
    static = client.get("/ops/static/ops.js")
    assert static.status_code == 200
    assert "KartmaX GA4 Ops Console" in static.text


def test_is_ops_console_enabled_env():
    with patch.dict("os.environ", {"ENABLE_OPS_CONSOLE": "true"}, clear=False):
        assert is_ops_console_enabled() is True
    with patch.dict("os.environ", {"ENABLE_OPS_CONSOLE": "false"}, clear=False):
        assert is_ops_console_enabled() is False