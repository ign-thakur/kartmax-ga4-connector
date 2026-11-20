from __future__ import annotations

import time
from typing import Any

import jwt

from src.api.auth.clients import OAuthClient
from src.api.auth.config import (
    get_access_token_ttl_seconds,
    get_jwt_audience,
    get_jwt_issuer,
    get_jwt_signing_secret,
)

JWT_ALGORITHM = "HS256"


def issue_access_token(client: OAuthClient) -> tuple[str, int, str]:
    ttl = get_access_token_ttl_seconds()
    now = int(time.time())
    scope = " ".join(sorted(client.scopes))
    payload: dict[str, Any] = {
        "iss": get_jwt_issuer(),
        "aud": get_jwt_audience(),
        "sub": client.client_id,
        "iat": now,
        "nbf": now,
        "exp": now + ttl,
        "scope": scope,
        "properties": sorted(client.property_ids),
        "client_id": client.client_id,
    }
    token = jwt.encode(payload, get_jwt_signing_secret(), algorithm=JWT_ALGORITHM)
    return token, ttl, scope


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        get_jwt_signing_secret(),
        algorithms=[JWT_ALGORITHM],
        audience=get_jwt_audience(),
        issuer=get_jwt_issuer(),
        options={
            "require": ["exp", "iat", "iss", "aud", "sub", "scope", "properties", "client_id"],
        },
    )


def scopes_from_claims(claims: dict[str, Any]) -> frozenset[str]:
    raw = claims.get("scope") or ""
    return frozenset(part for part in str(raw).split() if part)


def properties_from_claims(claims: dict[str, Any]) -> frozenset[str]:
    raw = claims.get("properties") or []
    if not isinstance(raw, list):
        return frozenset()
    return frozenset(str(pid).strip() for pid in raw if str(pid).strip())