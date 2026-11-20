"""Service account access tokens for MCP HTTP Bearer authentication."""

from __future__ import annotations

import logging
import threading
from typing import Final

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from src.config.settings import get_credentials_path

logger = logging.getLogger(__name__)

ANALYTICS_READONLY_SCOPE: Final = "https://www.googleapis.com/auth/analytics.readonly"


class ServiceAccountTokenError(Exception):
    """Could not load or refresh the service account access token."""


class ServiceAccountTokenProvider:
    """Caches service account credentials and refreshes the access token when needed."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._credentials: service_account.Credentials | None = None

    def _ensure_credentials(self) -> service_account.Credentials:
        if self._credentials is None:
            path = get_credentials_path()
            try:
                self._credentials = (
                    service_account.Credentials.from_service_account_file(
                        str(path),
                        scopes=[ANALYTICS_READONLY_SCOPE],
                    )
                )
            except FileNotFoundError as exc:
                raise ServiceAccountTokenError(
                    "Google service account credentials file was not found. "
                    "Check GOOGLE_APPLICATION_CREDENTIALS."
                ) from exc
            except (ValueError, OSError) as exc:
                raise ServiceAccountTokenError(
                    "Google service account credentials file is invalid or unreadable."
                ) from exc
        return self._credentials

    def get_bearer_token(self) -> str:
        """Return a valid access token, refreshing only when expired or missing."""
        with self._lock:
            credentials = self._ensure_credentials()
            if not credentials.valid:
                try:
                    credentials.refresh(Request())
                except RefreshError as exc:
                    raise ServiceAccountTokenError(
                        "Failed to refresh Google access token. "
                        "Verify the service account key is valid and not revoked."
                    ) from exc
                except OSError as exc:
                    raise ServiceAccountTokenError(
                        "Network error while refreshing Google access token."
                    ) from exc
            token = credentials.token
            if not token:
                raise ServiceAccountTokenError(
                    "Google access token is missing after refresh."
                )
            return token

    def authorization_header(self) -> dict[str, str]:
        token = self.get_bearer_token()
        return {"Authorization": f"Bearer {token}"}


_default_provider: ServiceAccountTokenProvider | None = None
_provider_lock = threading.Lock()


def get_token_provider() -> ServiceAccountTokenProvider:
    global _default_provider
    with _provider_lock:
        if _default_provider is None:
            _default_provider = ServiceAccountTokenProvider()
        return _default_provider


def get_mcp_authorization_headers() -> dict[str, str]:
    """Bearer header for authenticated MCP HTTP requests."""
    try:
        return get_token_provider().authorization_header()
    except FileNotFoundError as exc:
        raise ServiceAccountTokenError(
            "GOOGLE_APPLICATION_CREDENTIALS is not set or points to a missing file."
        ) from exc
    except ValueError as exc:
        raise ServiceAccountTokenError(str(exc)) from exc