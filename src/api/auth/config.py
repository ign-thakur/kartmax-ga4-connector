from __future__ import annotations

import os

DEFAULT_JWT_ISSUER = "kartmax-ga4-connector"
DEFAULT_JWT_AUDIENCE = "kartmax-backend"
DEFAULT_ACCESS_TOKEN_TTL_SECONDS = 30 * 60


def get_jwt_signing_secret() -> str:
    secret = os.getenv("JWT_SIGNING_SECRET", "").strip()
    if not secret:
        raise ValueError("JWT_SIGNING_SECRET is not configured.")
    if len(secret) < 32:
        raise ValueError("JWT_SIGNING_SECRET must be at least 32 characters.")
    return secret


def get_jwt_issuer() -> str:
    return os.getenv("JWT_ISSUER", DEFAULT_JWT_ISSUER).strip() or DEFAULT_JWT_ISSUER


def get_jwt_audience() -> str:
    return os.getenv("JWT_AUDIENCE", DEFAULT_JWT_AUDIENCE).strip() or DEFAULT_JWT_AUDIENCE


def get_access_token_ttl_seconds() -> int:
    raw = os.getenv("JWT_ACCESS_TOKEN_TTL_SECONDS", str(DEFAULT_ACCESS_TOKEN_TTL_SECONDS)).strip()
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_ACCESS_TOKEN_TTL_SECONDS
    if value < 60 or value > 24 * 60 * 60:
        return DEFAULT_ACCESS_TOKEN_TTL_SECONDS
    return value


def jwt_auth_enabled() -> bool:
    return bool(os.getenv("JWT_SIGNING_SECRET", "").strip())