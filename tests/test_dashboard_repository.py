import json

import pytest

from src.dashboard import repository


def test_list_reports_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "OUTPUT_DIR", tmp_path)
    assert repository.list_reports() == []


def test_load_report_rejects_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "OUTPUT_DIR", tmp_path)
    with pytest.raises((ValueError, FileNotFoundError)):
        repository.load_report("../outside.json")


def test_aggregate_by_channel_in_range(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "OUTPUT_DIR", tmp_path)
    payload = {
        "report_type": "gmv_by_channel",
        "property_id": "123",
        "currency": "INR",
        "data": [
            {"date": "2026-11-01", "channel": "Direct", "gmv": "100"},
            {"date": "2026-11-02", "channel": "Direct", "gmv": "50"},
            {"date": "2026-11-02", "channel": "Organic Search", "gmv": "25"},
            {"date": "2026-11-05", "channel": "Direct", "gmv": "999"},
        ],
    }
    path = tmp_path / "gmv_by_channel_20261105.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = repository.get_dashboard_data("2026-11-01", "2026-11-02")
    assert result["currency"] == "INR"
    gmv = {row["channel"]: row["gmv"] for row in result["gmv_by_channel"]}
    assert gmv["Direct"] == 150.0
    assert gmv["Organic Search"] == 25.0