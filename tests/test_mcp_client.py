import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx2
import pytest

from src.mcp.client import (
    RUN_REPORT_TOOL,
    McpAuthError,
    McpClientError,
    _tool_names_from_list_tools,
    call_mcp_tool,
    check_mcp_connectivity,
)
from src.mcp.settings import get_mcp_timeout_seconds, redact_url_for_logs


def test_redact_url_for_logs_strips_password():
    assert (
        redact_url_for_logs("http://user:secret@127.0.0.1:8000/mcp")
        == "http://user:***@127.0.0.1:8000/mcp"
    )


def test_tool_names_from_list_tools():
    result = SimpleNamespace(
        tools=[SimpleNamespace(name="run_report"), SimpleNamespace(name="get_account_summaries")]
    )
    assert _tool_names_from_list_tools(result) == ["run_report", "get_account_summaries"]


@patch.dict("os.environ", {"MCP_SERVER_URL": "http://127.0.0.1:8000/mcp", "MCP_TIMEOUT": "45"})
def test_get_mcp_timeout_seconds_from_env():
    assert get_mcp_timeout_seconds() == 45.0


@patch("src.mcp.client.Client")
@patch("src.mcp.client.streamable_http_client")
@patch("src.mcp.client._create_http_client")
@patch.dict("os.environ", {"MCP_SERVER_URL": "http://127.0.0.1:8000/mcp"})
def test_check_mcp_connectivity_success(mock_http_factory, mock_transport, mock_client_cls):
    mock_http_factory.return_value.__aenter__ = AsyncMock(
        return_value=MagicMock()
    )
    mock_http_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    mock_transport.return_value = object()

    session = AsyncMock()
    session.list_tools = AsyncMock(
        return_value=SimpleNamespace(
            tools=[
                SimpleNamespace(name=RUN_REPORT_TOOL),
                SimpleNamespace(name="run_realtime_report"),
            ]
        )
    )
    mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

    result = asyncio.run(check_mcp_connectivity())

    assert result.ok
    assert result.connected
    assert result.run_report_available
    assert RUN_REPORT_TOOL in result.tool_names


@patch("src.mcp.client.Client")
@patch("src.mcp.client.streamable_http_client")
@patch("src.mcp.client._create_http_client")
@patch.dict("os.environ", {"MCP_SERVER_URL": "http://127.0.0.1:8000/mcp"})
def test_check_mcp_connectivity_missing_run_report(
    mock_http_factory, mock_transport, mock_client_cls
):
    mock_http_factory.return_value.__aenter__ = AsyncMock(
        return_value=MagicMock()
    )
    mock_http_factory.return_value.__aexit__ = AsyncMock(return_value=None)
    mock_transport.return_value = object()

    session = AsyncMock()
    session.list_tools = AsyncMock(
        return_value=SimpleNamespace(tools=[SimpleNamespace(name="other_tool")])
    )
    mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

    result = asyncio.run(check_mcp_connectivity())

    assert result.connected
    assert not result.run_report_available
    assert not result.ok
    assert result.error_message


@patch("src.mcp.client.Client")
@patch("src.mcp.client.streamable_http_client")
@patch("src.mcp.client._create_http_client")
@patch.dict("os.environ", {"MCP_SERVER_URL": "http://127.0.0.1:8000/mcp"})
def test_check_mcp_connectivity_timeout(mock_http_factory, mock_transport, mock_client_cls):
    mock_http_factory.return_value.__aenter__ = AsyncMock(
        return_value=MagicMock()
    )
    mock_http_factory.return_value.__aexit__ = AsyncMock(return_value=None)
    mock_transport.return_value = object()

    mock_client_cls.return_value.__aenter__ = AsyncMock(
        side_effect=httpx2.TimeoutException("timed out")
    )
    mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

    result = asyncio.run(check_mcp_connectivity())

    assert not result.connected
    assert "timed out" in (result.error_message or "").lower()


@patch.dict("os.environ", {}, clear=True)
def test_check_mcp_connectivity_missing_url():
    with pytest.raises(McpClientError, match="MCP_SERVER_URL"):
        asyncio.run(check_mcp_connectivity())


@patch("src.mcp.client.Client")
@patch("src.mcp.client.streamable_http_client")
@patch("src.mcp.client._create_http_client")
@patch("src.mcp.client.get_mcp_authorization_headers")
@patch.dict(
    "os.environ",
    {
        "MCP_SERVER_URL": "http://127.0.0.1:8000/mcp",
        "GA4_PROPERTY_ID": "352673114",
    },
)
def test_call_mcp_tool_authenticated(
    mock_headers, mock_http_factory, mock_transport, mock_client_cls
):
    mock_headers.return_value = {"Authorization": "Bearer sa-token"}
    mock_http_factory.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
    mock_http_factory.return_value.__aexit__ = AsyncMock(return_value=None)
    mock_transport.return_value = object()

    session = AsyncMock()
    session.call_tool = AsyncMock(return_value=SimpleNamespace(is_error=False))
    mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

    asyncio.run(call_mcp_tool("run_report", {"property_id": "1"}))

    mock_headers.assert_called_once()
    session.call_tool.assert_awaited_once()


@patch("src.mcp.client.get_mcp_authorization_headers")
@patch.dict("os.environ", {"MCP_SERVER_URL": "http://127.0.0.1:8000/mcp"})
def test_call_mcp_tool_auth_failure_raises(mock_headers):
    from src.mcp.tokens import ServiceAccountTokenError

    mock_headers.side_effect = ServiceAccountTokenError("credentials missing")

    with pytest.raises(McpAuthError, match="credentials"):
        asyncio.run(call_mcp_tool("run_report", {}, authenticated=True))