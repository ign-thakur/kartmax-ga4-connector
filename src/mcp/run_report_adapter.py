"""Fetch GA4 source reports via MCP ``run_report`` and normalize rows."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.clients.analytics_client import (
    extract_currency_from_dict,
    parse_source_metric_rows_from_dict,
)
from src.config.dates import ResolvedDateRange
from src.config.settings import get_property_id
from src.mcp.client import RUN_REPORT_TOOL, McpAuthError, McpClientError, call_mcp_tool
from src.mcp.report_queries import REPORT_LIMIT, SOURCE_REPORT_DIMENSIONS
from src.mcp.run_report import _parse_json_blob, _tool_text_payload, redact_sensitive_text

logger = logging.getLogger(__name__)


class McpRunReportError(Exception):
    """MCP run_report failed or returned an unusable payload."""


def build_date_range_argument(date_range: ResolvedDateRange) -> dict[str, str]:
    return {
        "start_date": date_range.start_date,
        "end_date": date_range.end_date,
    }


def build_run_report_arguments(
    *,
    metric_name: str,
    date_range: ResolvedDateRange,
    property_id: str | None = None,
) -> dict[str, Any]:
    pid = property_id or get_property_id()
    return {
        "property_id": pid,
        "date_ranges": [build_date_range_argument(date_range)],
        "dimensions": list(SOURCE_REPORT_DIMENSIONS),
        "metrics": [metric_name],
        "limit": REPORT_LIMIT,
    }


def _raise_on_tool_error(tool_result: Any) -> dict[str, Any]:
    if getattr(tool_result, "is_error", False):
        raw = redact_sensitive_text(_tool_text_payload(tool_result))
        payload = _parse_json_blob(raw)
        if isinstance(payload, dict) and payload.get("error"):
            raise McpRunReportError(str(payload["error"]))
        raise McpRunReportError(raw or "MCP run_report returned an error.")

    text = _tool_text_payload(tool_result)
    payload = _parse_json_blob(text)
    if not isinstance(payload, dict):
        raise McpRunReportError("MCP run_report returned non-JSON content.")
    if payload.get("error"):
        raise McpRunReportError(redact_sensitive_text(str(payload["error"])))
    return payload


async def run_report_via_mcp_async(
    *,
    metric_name: str,
    date_range: ResolvedDateRange,
    value_key: str,
    property_id: str | None = None,
) -> tuple[str, list[dict[str, Any]], str | None]:
    pid = property_id or get_property_id()
    arguments = build_run_report_arguments(
        metric_name=metric_name,
        date_range=date_range,
        property_id=pid,
    )
    try:
        tool_result = await call_mcp_tool(
            RUN_REPORT_TOOL,
            arguments,
            authenticated=True,
        )
    except McpAuthError as exc:
        raise McpRunReportError(str(exc)) from exc
    except McpClientError as exc:
        raise McpRunReportError(str(exc)) from exc

    payload = _raise_on_tool_error(tool_result)
    data = parse_source_metric_rows_from_dict(payload, value_key=value_key)
    currency = extract_currency_from_dict(payload)
    logger.info(
        "MCP run_report metric=%s property=%s rows=%s",
        metric_name,
        pid,
        len(data),
    )
    return pid, data, currency


def run_report_via_mcp(
    *,
    metric_name: str,
    date_range: ResolvedDateRange,
    value_key: str,
    property_id: str | None = None,
) -> tuple[str, list[dict[str, Any]], str | None]:
    """Synchronous entry for report modules and CLI."""
    return asyncio.run(
        run_report_via_mcp_async(
            metric_name=metric_name,
            date_range=date_range,
            value_key=value_key,
            property_id=property_id,
        )
    )