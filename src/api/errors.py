"""Map report/MCP exceptions to HTTP responses."""

from __future__ import annotations

from fastapi import HTTPException, status


def _is_permission_denied(message: str) -> bool:
    lowered = message.lower()
    return any(
        token in lowered
        for token in (
            "permission",
            "forbidden",
            "403",
            "denied",
            "insufficient",
        )
    )


def _is_auth_failure(message: str) -> bool:
    lowered = message.lower()
    return any(
        token in lowered
        for token in (
            "oauth",
            "access token",
            "credentials",
            "refresh",
            "unauthorized",
            "service account",
        )
    )


def http_error_from_report_failure(exc: Exception) -> HTTPException:
    message = str(exc)
    if _is_permission_denied(message):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="GA4 denied access for this property or report.",
        )
    if _is_auth_failure(message):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google authentication failed for MCP report execution.",
        )
    if "timed out" in message.lower() or "connection failed" in message.lower():
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics MCP server is unavailable.",
        )
    if "no data rows" in message.lower():
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GA4 returned no data for the requested property and date range.",
        )
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Failed to fetch report from Analytics MCP.",
    )