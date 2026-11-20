from __future__ import annotations

from fastapi import HTTPException, status

from src.api.auth.context import BackendAuthContext
from src.api.auth.scopes import SCOPE_GMV, SCOPE_SESSIONS
from src.reports.gmv_by_channel import REPORT_TYPE as GMV_REPORT_TYPE
from src.reports.sessions_by_channel import REPORT_TYPE as SESSIONS_REPORT_TYPE

_REPORT_SCOPE = {
    GMV_REPORT_TYPE: SCOPE_GMV,
    SESSIONS_REPORT_TYPE: SCOPE_SESSIONS,
}


def validate_export_auth(auth: BackendAuthContext, report_types: list[str]) -> None:
    if auth.method == "api_key":
        return
    needed = {_REPORT_SCOPE[rt] for rt in report_types if rt in _REPORT_SCOPE}
    if not needed.issubset(auth.scopes):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient token scope for requested report exports.",
        )