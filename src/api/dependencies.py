"""FastAPI dependencies for KartmaX Backend API."""

from __future__ import annotations

import os
import secrets
from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.api.auth.config import jwt_auth_enabled
from src.api.auth.context import BackendAuthContext
from src.api.auth.tokens import decode_access_token, properties_from_claims, scopes_from_claims

_bearer = HTTPBearer(auto_error=False)


def _auth_context_from_bearer(token: str) -> BackendAuthContext:
    if not jwt_auth_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT authentication is not configured on this connector.",
        )
    try:
        claims = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired.",
        ) from None
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed access token.",
        ) from None

    client_id = str(claims.get("client_id") or claims.get("sub") or "").strip()
    scopes = scopes_from_claims(claims)
    properties = properties_from_claims(claims)
    if not client_id or not scopes or not properties:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token claims.",
        )
    return BackendAuthContext(
        method="bearer",
        client_id=client_id,
        scopes=scopes,
        property_ids=properties,
    )


def verify_backend_auth(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> BackendAuthContext:
    if credentials is not None and credentials.scheme.lower() == "bearer":
        return _auth_context_from_bearer(credentials.credentials)

    if x_api_key:
        expected = os.getenv("KARTMAX_API_KEY", "").strip()
        if expected and secrets.compare_digest(x_api_key, expected):
            return BackendAuthContext(
                method="api_key",
                client_id=None,
                scopes=frozenset(),
                property_ids=None,
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication. Use Bearer token or X-API-Key.",
    )


def require_scopes(*required_scopes: str) -> Callable[..., BackendAuthContext]:
    needed = frozenset(required_scopes)

    def _dependency(
        auth: Annotated[BackendAuthContext, Depends(verify_backend_auth)],
    ) -> BackendAuthContext:
        if auth.method == "api_key":
            return auth
        if not needed.issubset(auth.scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient token scope.",
            )
        return auth

    return _dependency


def authorize_property_access(auth: BackendAuthContext, property_id: str) -> None:
    if auth.property_ids is None:
        return
    if property_id not in auth.property_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token is not authorized for this GA4 property.",
        )