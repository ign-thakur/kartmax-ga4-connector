from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from google.auth.exceptions import RefreshError

from src.mcp.client import _create_http_client
from src.mcp.tokens import (
    ServiceAccountTokenError,
    ServiceAccountTokenProvider,
    get_mcp_authorization_headers,
)


def test_create_http_client_sends_authorization_header():
    with patch(
        "src.mcp.client.get_mcp_authorization_headers",
        return_value={"Authorization": "Bearer test-token"},
    ):
        client = _create_http_client(authenticated=True)
        assert client.headers.get("Authorization") == "Bearer test-token"


def test_create_http_client_unauthenticated_has_no_authorization():
    client = _create_http_client(authenticated=False)
    assert "Authorization" not in client.headers


@patch("src.mcp.tokens.get_credentials_path")
def test_provider_returns_cached_token_when_valid(mock_path):
    mock_path.return_value = __file__
    provider = ServiceAccountTokenProvider()
    creds = MagicMock()
    creds.valid = True
    creds.token = "cached-token"
    provider._credentials = creds

    assert provider.get_bearer_token() == "cached-token"
    creds.refresh.assert_not_called()


@patch("src.mcp.tokens.Request")
@patch("src.mcp.tokens.service_account.Credentials.from_service_account_file")
@patch("src.mcp.tokens.get_credentials_path")
def test_provider_refreshes_when_invalid(
    mock_path, mock_from_file, mock_request
):
    mock_path.return_value = __file__
    creds = MagicMock()
    creds.valid = False
    creds.token = "fresh-token"
    mock_from_file.return_value = creds

    provider = ServiceAccountTokenProvider()
    token = provider.get_bearer_token()

    assert token == "fresh-token"
    creds.refresh.assert_called_once()


@patch("src.mcp.tokens.Request")
@patch("src.mcp.tokens.service_account.Credentials.from_service_account_file")
@patch("src.mcp.tokens.get_credentials_path")
def test_provider_refresh_error(mock_path, mock_from_file, mock_request):
    mock_path.return_value = __file__
    creds = MagicMock()
    creds.valid = False
    creds.refresh.side_effect = RefreshError("revoked")
    mock_from_file.return_value = creds

    provider = ServiceAccountTokenProvider()
    with pytest.raises(ServiceAccountTokenError, match="refresh"):
        provider.get_bearer_token()


@patch("src.mcp.tokens.get_token_provider")
def test_get_mcp_authorization_header_shape(mock_get_provider):
    mock_provider = MagicMock()
    mock_provider.authorization_header.return_value = {
        "Authorization": "Bearer abc"
    }
    mock_get_provider.return_value = mock_provider

    assert get_mcp_authorization_headers() == {"Authorization": "Bearer abc"}