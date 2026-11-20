"""Runtime profile flags (API-only vs dashboard vs ops console)."""

from __future__ import annotations

import os

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _env_truthy(name: str, default: str) -> bool:
    raw = os.getenv(name, default).strip().lower()
    return raw in _TRUTHY


def is_dashboard_enabled() -> bool:
    """When false, legacy JSON dashboard routes are not exposed."""
    return _env_truthy("ENABLE_DASHBOARD", "true")


def is_ops_console_enabled() -> bool:
    """JWT-authenticated ops UI (static). No server-side secrets; uses v1 APIs only."""
    return _env_truthy("ENABLE_OPS_CONSOLE", "false")