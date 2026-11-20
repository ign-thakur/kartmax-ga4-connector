from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, status

from src.api.auth.clients import authenticate_client_credentials
from src.api.auth.config import jwt_auth_enabled
from src.api.auth.tokens import issue_access_token
from src.api.schemas import TokenResponse

router = APIRouter(tags=["auth"])


@router.post("/auth/token", response_model=TokenResponse)
def issue_token(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
) -> TokenResponse:
    if not jwt_auth_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT authentication is not configured on this connector.",
        )
    if grant_type.strip() != "client_credentials":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported grant_type. Use client_credentials.",
        )
    client = authenticate_client_credentials(
        client_id.strip(),
        client_secret,
    )
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client credentials.",
        )
    access_token, expires_in, scope = issue_access_token(client)
    return TokenResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=expires_in,
        scope=scope,
    )