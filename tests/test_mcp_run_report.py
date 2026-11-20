import json
from types import SimpleNamespace

from src.mcp.run_report import parse_run_report_smoke, redact_sensitive_text


def test_redact_sensitive_text_masks_bearer():
    text = "Failed: Authorization Bearer ya29.secret-value-here"
    assert "ya29" not in redact_sensitive_text(text)
    assert "Bearer ***" in redact_sensitive_text(text)


def test_parse_run_report_smoke_success():
    payload = {
        "rows": [
            {
                "metric_values": [{"value": "42"}],
            }
        ]
    }
    tool_result = SimpleNamespace(
        is_error=False,
        content=[SimpleNamespace(text=json.dumps(payload))],
    )
    parsed = parse_run_report_smoke(property_id="352673114", tool_result=tool_result)
    assert parsed.ok
    assert parsed.sessions_value == "42"
    assert parsed.row_count == 1


def test_parse_run_report_smoke_tool_error():
    tool_result = SimpleNamespace(
        is_error=True,
        content=[
            SimpleNamespace(
                text=json.dumps({"error": "Missing OAuth access token"})
            )
        ],
    )
    parsed = parse_run_report_smoke(property_id="352673114", tool_result=tool_result)
    assert not parsed.ok
    assert "OAuth" in (parsed.error_message or "")