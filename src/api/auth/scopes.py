"""OAuth scopes for KartmaX Backend JWT access tokens."""

SCOPE_GMV = "reports:gmv"
SCOPE_SESSIONS = "reports:sessions"
SCOPE_HEALTH = "health:read"

DEFAULT_CLIENT_SCOPES = (SCOPE_GMV, SCOPE_SESSIONS, SCOPE_HEALTH)