from fastapi import APIRouter, Depends, HTTPException, Query, status

from typing import Annotated

from src.api.auth.context import BackendAuthContext
from src.api.auth.scopes import SCOPE_GMV, SCOPE_SESSIONS
from src.api.dependencies import authorize_property_access, require_scopes
from src.api.errors import http_error_from_report_failure
from src.mcp.run_report_adapter import McpRunReportError

from src.api.service import fetch_gmv_report_for_api, fetch_sessions_report_for_api

router = APIRouter(tags=["reports"])


@router.get("/reports/gmv-by-source")
def get_gmv_by_source(
    auth: Annotated[BackendAuthContext, Depends(require_scopes(SCOPE_GMV))],
    property_id: str = Query(..., min_length=1, max_length=12),
    start_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
):
    authorize_property_access(auth, property_id)
    try:
        return fetch_gmv_report_for_api(
            property_id=property_id,
            start_date=start_date,
            end_date=end_date,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except McpRunReportError as exc:
        raise http_error_from_report_failure(exc) from exc
    except Exception as exc:
        raise http_error_from_report_failure(exc) from exc


@router.get("/reports/sessions-by-source")
def get_sessions_by_source(
    auth: Annotated[BackendAuthContext, Depends(require_scopes(SCOPE_SESSIONS))],
    property_id: str = Query(..., min_length=1, max_length=12),
    start_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
):
    authorize_property_access(auth, property_id)
    try:
        return fetch_sessions_report_for_api(
            property_id=property_id,
            start_date=start_date,
            end_date=end_date,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except McpRunReportError as exc:
        raise http_error_from_report_failure(exc) from exc
    except Exception as exc:
        raise http_error_from_report_failure(exc) from exc