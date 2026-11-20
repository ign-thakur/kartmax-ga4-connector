from __future__ import annotations

import json
import os
import secrets
from dataclasses import dataclass

from src.api.auth.scopes import DEFAULT_CLIENT_SCOPES


@dataclass(frozen=True)
class OAuthClient:
    client_id: str
    client_secret: str
    property_ids: frozenset[str]
    scopes: frozenset[str]


def _parse_clients_payload(raw: str) -> list[dict]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("KARTMAX_OAUTH_CLIENTS must be valid JSON.") from exc
    if not isinstance(data, list) or not data:
        raise ValueError("KARTMAX_OAUTH_CLIENTS must be a non-empty JSON array.")
    return data


def load_oauth_clients() -> dict[str, OAuthClient]:
    raw = os.getenv("KARTMAX_OAUTH_CLIENTS", "").strip()
    if not raw:
        raise ValueError("KARTMAX_OAUTH_CLIENTS is not configured.")

    clients: dict[str, OAuthClient] = {}
    for entry in _parse_clients_payload(raw):
        if not isinstance(entry, dict):
            continue
        client_id = str(entry.get("client_id") or "").strip()
        client_secret = str(entry.get("client_secret") or "").strip()
        if not client_id or not client_secret:
            continue
        raw_properties = entry.get("property_ids") or []
        if not isinstance(raw_properties, list) or not raw_properties:
            raise ValueError(f"Client {client_id!r} must define property_ids.")
        property_ids = frozenset(str(pid).strip() for pid in raw_properties if str(pid).strip())
        if not property_ids:
            raise ValueError(f"Client {client_id!r} must define at least one property_id.")

        raw_scopes = entry.get("scopes")
        if raw_scopes is None:
            scopes = frozenset(DEFAULT_CLIENT_SCOPES)
        elif isinstance(raw_scopes, list):
            scopes = frozenset(str(s).strip() for s in raw_scopes if str(s).strip())
        else:
            raise ValueError(f"Client {client_id!r} scopes must be a list.")
        if not scopes:
            raise ValueError(f"Client {client_id!r} must define at least one scope.")

        clients[client_id] = OAuthClient(
            client_id=client_id,
            client_secret=client_secret,
            property_ids=property_ids,
            scopes=scopes,
        )
    if not clients:
        raise ValueError("KARTMAX_OAUTH_CLIENTS contains no valid clients.")
    return clients


def authenticate_client_credentials(client_id: str, client_secret: str) -> OAuthClient | None:
    try:
        clients = load_oauth_clients()
    except ValueError:
        return None
    client = clients.get(client_id)
    if client is None:
        return None
    if not secrets.compare_digest(client_secret, client.client_secret):
        return None
    return client