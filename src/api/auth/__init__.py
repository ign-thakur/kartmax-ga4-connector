"""Server-to-server auth (JWT client credentials + legacy API key)."""

from src.api.auth.context import BackendAuthContext
from src.api.auth.scopes import SCOPE_GMV, SCOPE_HEALTH, SCOPE_SESSIONS

__all__ = [
    "BackendAuthContext",
    "SCOPE_GMV",
    "SCOPE_HEALTH",
    "SCOPE_SESSIONS",
]