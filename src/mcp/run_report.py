"""Helpers for parsing MCP run_report results (smoke tests; not full report migration)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

_SENSITIVE = re.compile(
    r"(Bearer\s+[A-Za-z0-9._\-+/=]+|ya29\.[A-Za-z0-9._\-+/=]+)",
    re.IGNORECASE,
)


def redact_sensitive_text(text: str) -> str:
    return _SENSITIVE.sub("Bearer ***", text)


@dataclass(frozen=True)
class RunReportSmokeResult:
    property_id: str
    ok: bool
    row_count: int
    sessions_value: str | None
    error_message: str | None = None

    @property
    def summary(self) -> str:
        if not self.ok:
            return self.error_message or "run_report failed"
        if self.sessions_value is not None:
            return (
                f"yesterday sessions={self.sessions_value} "
                f"(rows={self.row_count}, property={self.property_id})"
            )
        return f"rows={self.row_count} (property={self.property_id})"


def _tool_text_payload(result: Any) -> str:
    content = getattr(result, "content", None) or []
    parts: list[str] = []
    for block in content:
        text = getattr(block, "text", None)
        if text is None and isinstance(block, dict):
            text = block.get("text")
        if text:
            parts.append(str(text))
    return "\n".join(parts)


def _parse_json_blob(text: str) -> Any:
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _sessions_from_ga4_payload(payload: Any) -> tuple[int, str | None]:
    """Extract row count and sessions metric from MCP/GA4 JSON."""
    if not isinstance(payload, dict):
        return 0, None

    rows = payload.get("rows")
    if not isinstance(rows, list):
        rows = []

    sessions_value: str | None = None
    if rows:
        first = rows[0]
        if isinstance(first, dict):
            metric_values = first.get("metric_values") or first.get("metricValues")
            if isinstance(metric_values, list) and metric_values:
                mv0 = metric_values[0]
                if isinstance(mv0, dict):
                    sessions_value = mv0.get("value")
                elif hasattr(mv0, "value"):
                    sessions_value = mv0.value

    return len(rows), sessions_value


def parse_run_report_smoke(
    *,
    property_id: str,
    tool_result: Any,
) -> RunReportSmokeResult:
    if getattr(tool_result, "is_error", False):
        raw = redact_sensitive_text(_tool_text_payload(tool_result))
        try:
            err_obj = _parse_json_blob(raw)
            if isinstance(err_obj, dict) and err_obj.get("error"):
                msg = redact_sensitive_text(str(err_obj["error"]))
            else:
                msg = raw or "MCP run_report returned an error."
        except Exception:
            msg = raw or "MCP run_report returned an error."
        return RunReportSmokeResult(
            property_id=property_id,
            ok=False,
            row_count=0,
            sessions_value=None,
            error_message=msg,
        )

    text = _tool_text_payload(tool_result)
    payload = _parse_json_blob(text)
    if payload is None:
        return RunReportSmokeResult(
            property_id=property_id,
            ok=False,
            row_count=0,
            sessions_value=None,
            error_message="MCP run_report returned non-JSON content.",
        )

    if isinstance(payload, dict) and payload.get("error"):
        return RunReportSmokeResult(
            property_id=property_id,
            ok=False,
            row_count=0,
            sessions_value=None,
            error_message=redact_sensitive_text(str(payload["error"])),
        )

    row_count, sessions_value = _sessions_from_ga4_payload(payload)
    return RunReportSmokeResult(
        property_id=property_id,
        ok=True,
        row_count=row_count,
        sessions_value=sessions_value,
        error_message=None,
    )