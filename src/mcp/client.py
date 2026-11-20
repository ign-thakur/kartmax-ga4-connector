"""MCP HTTP client for Google's analytics-mcp server (Streamable HTTP only)."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from src.config.settings import get_property_id
from src.mcp.run_report import RunReportSmokeResult, parse_run_report_smoke
from src.mcp.settings import (
    get_mcp_read_timeout_seconds,
    get_mcp_server_url,
    get_mcp_timeout_seconds,
    redact_url_for_logs,
)
from src.mcp.tokens import ServiceAccountTokenError, get_mcp_authorization_headers

logger = logging.getLogger(__name__)

RUN_REPORT_TOOL = "run_report"

MCP_CLIENT_INFO_NAME = "kartmax-ga4-connector"
MCP_CLIENT_INFO_VERSION = "0.2.0"


class McpClientError(Exception):
    """Failed to reach or use the Analytics MCP server over HTTP."""


class McpAuthError(McpClientError):
    """Service account token could not be loaded or refreshed."""


@dataclass(frozen=True)
class McpConnectivityResult:
    server_url: str
    connected: bool
    tool_names: tuple[str, ...]
    run_report_available: bool
    error_message: str | None = None

    @property
    def ok(self) -> bool:
        return self.connected and self.run_report_available and not self.error_message


def _http_timeout() -> httpx2.Timeout:
    return httpx2.Timeout(
        get_mcp_timeout_seconds(),
        read=get_mcp_read_timeout_seconds(),
    )


def _create_http_client(*, authenticated: bool = False) -> httpx2.AsyncClient:
    headers: dict[str, str] = {}
    if authenticated:
        headers.update(get_mcp_authorization_headers())
    return httpx2.AsyncClient(timeout=_http_timeout(), headers=headers)


def _root_cause(exc: BaseException) -> BaseException:
    """Unwrap TaskGroup / ExceptionGroup wrappers from the MCP transport."""
    current: BaseException = exc
    while isinstance(current, BaseExceptionGroup) and current.exceptions:
        current = current.exceptions[0]
    if current.__cause__ is not None:
        return _root_cause(current.__cause__)
    return current


def _transport_error_message(safe_url: str, exc: BaseException) -> str:
    root = _root_cause(exc)
    if isinstance(root, httpx2.TimeoutException):
        return (
            f"MCP request timed out after {get_mcp_timeout_seconds():g}s "
            f"(server {safe_url})."
        )
    if isinstance(root, httpx2.HTTPError):
        return f"MCP HTTP error for {safe_url}: {root.__class__.__name__}"
    return f"MCP connection failed for {safe_url}: {root.__class__.__name__}"


def _tool_names_from_list_tools(result: Any) -> list[str]:
    tools = getattr(result, "tools", None)
    if tools is None and isinstance(result, dict):
        tools = result.get("tools")
    if not tools:
        return []
    names: list[str] = []
    for tool in tools:
        name = getattr(tool, "name", None)
        if name is None and isinstance(tool, dict):
            name = tool.get("name")
        if name:
            names.append(str(name))
    return names


async def call_mcp_tool(
    name: str,
    arguments: dict[str, Any] | None = None,
    *,
    authenticated: bool = True,
) -> Any:
    """
    Invoke an MCP tool over Streamable HTTP.

    Authenticated calls send ``Authorization: Bearer`` from the service account.
    """
    try:
        url = get_mcp_server_url()
        safe_url = redact_url_for_logs(url)
    except ValueError as exc:
        raise McpClientError(str(exc)) from exc

    if authenticated:
        try:
            get_mcp_authorization_headers()
        except ServiceAccountTokenError as exc:
            logger.warning("MCP auth failed before HTTP call: %s", exc)
            raise McpAuthError(str(exc)) from exc

    try:
        async with _create_http_client(authenticated=authenticated) as http_client:
            transport = streamable_http_client(url, http_client=http_client)
            async with Client(transport) as client:
                return await client.call_tool(name, arguments or {})
    except ValueError as exc:
        logger.warning("MCP configuration error: %s", exc)
        raise McpClientError(str(exc)) from exc
    except ServiceAccountTokenError as exc:
        raise McpAuthError(str(exc)) from exc
    except (httpx2.TimeoutException, BaseExceptionGroup, httpx2.HTTPError) as exc:
        msg = _transport_error_message(safe_url, exc)
        logger.warning(msg)
        raise McpClientError(msg) from exc
    except Exception as exc:
        if isinstance(_root_cause(exc), httpx2.HTTPError):
            msg = _transport_error_message(safe_url, exc)
            logger.warning(msg)
            raise McpClientError(msg) from exc
        msg = _transport_error_message(safe_url, exc)
        logger.exception("Unexpected MCP client error")
        raise McpClientError(msg) from exc


async def check_mcp_connectivity() -> McpConnectivityResult:
    """Connect over Streamable HTTP, list tools, and confirm `run_report` is advertised."""
    try:
        url = get_mcp_server_url()
        safe_url = redact_url_for_logs(url)

        async with _create_http_client(authenticated=False) as http_client:
            transport = streamable_http_client(url, http_client=http_client)
            async with Client(transport) as client:
                list_result = await client.list_tools()
    except ValueError as exc:
        logger.warning("MCP configuration error: %s", exc)
        raise McpClientError(str(exc)) from exc
    except httpx2.TimeoutException:
        msg = (
            f"MCP request timed out after {get_mcp_timeout_seconds():g}s "
            f"(server {safe_url})."
        )
        logger.warning(msg)
        return McpConnectivityResult(
            server_url=safe_url,
            connected=False,
            tool_names=(),
            run_report_available=False,
            error_message=msg,
        )
    except BaseExceptionGroup as exc:
        msg = _transport_error_message(safe_url, exc)
        logger.warning(msg)
        return McpConnectivityResult(
            server_url=safe_url,
            connected=False,
            tool_names=(),
            run_report_available=False,
            error_message=msg,
        )
    except httpx2.HTTPError as exc:
        msg = f"MCP HTTP error for {safe_url}: {exc.__class__.__name__}"
        logger.warning(msg)
        return McpConnectivityResult(
            server_url=safe_url,
            connected=False,
            tool_names=(),
            run_report_available=False,
            error_message=msg,
        )
    except Exception as exc:
        root = _root_cause(exc)
        if isinstance(root, httpx2.HTTPError):
            msg = f"MCP HTTP error for {safe_url}: {root.__class__.__name__}"
            logger.warning(msg)
        else:
            msg = f"MCP connection failed for {safe_url}: {root.__class__.__name__}"
            logger.exception("Unexpected MCP client error")
        return McpConnectivityResult(
            server_url=safe_url,
            connected=False,
            tool_names=(),
            run_report_available=False,
            error_message=msg,
        )

    names = sorted(_tool_names_from_list_tools(list_result))
    run_report_available = RUN_REPORT_TOOL in names
    logger.info(
        "MCP connected to %s; %s tools; run_report=%s",
        safe_url,
        len(names),
        run_report_available,
    )
    return McpConnectivityResult(
        server_url=safe_url,
        connected=True,
        tool_names=tuple(names),
        run_report_available=run_report_available,
        error_message=None
        if run_report_available
        else f"Tool {RUN_REPORT_TOOL!r} not returned by MCP server.",
    )


async def run_report_smoke_test() -> RunReportSmokeResult:
    """
    Minimal live GA4 check via MCP ``run_report`` (sessions, yesterday).

    Validates that the official HTTP server accepts our service-account Bearer token.
    """
    property_id = get_property_id()
    arguments = {
        "property_id": property_id,
        "date_ranges": [{"start_date": "yesterday", "end_date": "yesterday"}],
        "dimensions": [],
        "metrics": ["sessions"],
    }
    try:
        tool_result = await call_mcp_tool(
            RUN_REPORT_TOOL,
            arguments,
            authenticated=True,
        )
    except McpAuthError as exc:
        return RunReportSmokeResult(
            property_id=property_id,
            ok=False,
            row_count=0,
            sessions_value=None,
            error_message=str(exc),
        )
    except McpClientError as exc:
        return RunReportSmokeResult(
            property_id=property_id,
            ok=False,
            row_count=0,
            sessions_value=None,
            error_message=str(exc),
        )

    parsed = parse_run_report_smoke(property_id=property_id, tool_result=tool_result)
    if parsed.ok:
        logger.info(
            "MCP run_report smoke OK property=%s rows=%s",
            property_id,
            parsed.row_count,
        )
    else:
        logger.warning(
            "MCP run_report smoke failed property=%s: %s",
            property_id,
            parsed.error_message,
        )
    return parsed


def run_mcp_connectivity_check() -> McpConnectivityResult:
    """Synchronous entry point for CLI and scripts."""
    return asyncio.run(check_mcp_connectivity())


def run_mcp_run_report_smoke_test() -> RunReportSmokeResult:
    """Synchronous entry point for CLI smoke test."""
    return asyncio.run(run_report_smoke_test())