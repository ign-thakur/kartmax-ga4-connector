from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.auth.context import BackendAuthContext
from src.api.auth.scopes import SCOPE_HEALTH
from src.api.dependencies import require_scopes
from src.api.service import build_health_response

router = APIRouter(tags=["health"])


@router.get("/health")
def get_health(
    _: Annotated[BackendAuthContext, Depends(require_scopes(SCOPE_HEALTH))],
):
    return build_health_response()