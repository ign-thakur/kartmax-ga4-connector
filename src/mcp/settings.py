import os
import re
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv

from src.config.settings import PROJECT_ROOT

load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_MCP_TIMEOUT_SECONDS = 30.0
DEFAULT_MCP_READ_TIMEOUT_SECONDS = 300.0
_MIN_TIMEOUT = 1.0
_MAX_TIMEOUT = 600.0

_URL_SCHEME = re.compile(r"^https?://", re.IGNORECASE)


def get_mcp_server_url() -> str:
    """MCP Streamable HTTP endpoint (e.g. http://127.0.0.1:8000/mcp)."""
    raw = os.getenv("MCP_SERVER_URL", "").strip()
    if not raw:
        raise ValueError(
            "MCP_SERVER_URL is not set. See docs/mcp-http-setup.md."
        )
    if not _URL_SCHEME.match(raw):
        raise ValueError(
            "MCP_SERVER_URL must start with http:// or https://."
        )
    return raw.rstrip("/")


def get_mcp_timeout_seconds() -> float:
    """Connect/write/pool timeout for MCP HTTP requests (seconds)."""
    raw = os.getenv("MCP_TIMEOUT", str(DEFAULT_MCP_TIMEOUT_SECONDS)).strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(
            f"MCP_TIMEOUT must be a number of seconds, got {raw!r}."
        ) from exc
    if value < _MIN_TIMEOUT or value > _MAX_TIMEOUT:
        raise ValueError(
            f"MCP_TIMEOUT must be between {_MIN_TIMEOUT} and {_MAX_TIMEOUT}."
        )
    return value


def get_mcp_read_timeout_seconds() -> float:
    """Read timeout for long-running MCP tool streams (seconds)."""
    return max(get_mcp_timeout_seconds(), DEFAULT_MCP_READ_TIMEOUT_SECONDS)


def redact_url_for_logs(url: str) -> str:
    """Strip userinfo from URLs so logs never contain embedded credentials."""
    parts = urlsplit(url)
    if not parts.username and not parts.password:
        return url
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    netloc = host
    if parts.username:
        netloc = f"{parts.username}:***@{host}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))