from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class BackendAuthContext:
    method: Literal["api_key", "bearer"]
    client_id: str | None
    scopes: frozenset[str]
    # None = unrestricted property access (legacy API key only).
    property_ids: frozenset[str] | None