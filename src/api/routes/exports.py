from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.auth.context import BackendAuthContext
from src.api.dependencies import authorize_property_access, verify_backend_auth
from src.api.export_auth import validate_export_auth
from src.api.schemas import GoogleSheetsExportRequest, GoogleSheetsExportResponse
from src.api.validation import validate_property_id, validate_report_date_range
from src.exports.sheets.constants import SPREADSHEET_ID_PATTERN
from src.exports.sheets.errors import (
    SheetsExportError,
    SheetsNotFoundError,
    SheetsPermissionError,
    SheetsTabError,
)
from src.exports.sheets.export_service import (
    export_reports_to_google_sheets,
    validate_report_types,
)

router = APIRouter(tags=["exports"])


def _validate_spreadsheet_id(spreadsheet_id: str) -> str:
    cleaned = spreadsheet_id.strip()
    if not SPREADSHEET_ID_PATTERN.match(cleaned):
        raise ValueError("spreadsheet_id format is invalid.")
    return cleaned


@router.post("/exports/google-sheets", response_model=GoogleSheetsExportResponse)
def export_google_sheets(
    body: GoogleSheetsExportRequest,
    auth: Annotated[BackendAuthContext, Depends(verify_backend_auth)],
) -> GoogleSheetsExportResponse:
    if auth.method != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google Sheets export requires Bearer JWT authentication.",
        )

    try:
        pid = validate_property_id(body.property_id)
        start, end = validate_report_date_range(body.start_date, body.end_date)
        sheet_id = _validate_spreadsheet_id(body.spreadsheet_id)
        report_types = validate_report_types([rt.strip() for rt in body.report_types])
        validate_export_auth(auth, report_types)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    authorize_property_access(auth, pid)

    try:
        payload = export_reports_to_google_sheets(
            property_id=pid,
            report_types=report_types,
            start_date=start,
            end_date=end,
            spreadsheet_id=sheet_id,
        )
    except SheetsPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except SheetsNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SheetsTabError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except SheetsExportError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Google Sheets export failed: {exc}",
        ) from exc

    return GoogleSheetsExportResponse.model_validate(payload)