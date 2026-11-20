from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GmvSourceRow(BaseModel):
    date: str
    source: str
    gmv: float


class SessionsSourceRow(BaseModel):
    date: str
    source: str
    sessions: float


class SourceReportResponse(BaseModel):
    success: bool = True
    report_type: str
    property_id: str
    start_date: str
    end_date: str
    currency: str | None = None
    data: list[Any] = Field(default_factory=list)


class HealthMcpStatus(BaseModel):
    connected: bool
    run_report_available: bool
    error_message: str | None = None


class HealthResponse(BaseModel):
    status: str
    connector: str
    mcp: HealthMcpStatus


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: str


class GoogleSheetsExportRequest(BaseModel):
    property_id: str
    report_types: list[str] = Field(..., min_length=1, max_length=2)
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    spreadsheet_id: str = Field(..., min_length=10, max_length=128)


class GoogleSheetsReportExportResult(BaseModel):
    report_type: str
    tab: str
    rows_exported: int
    rows_updated: int
    rows_inserted: int
    rows_total: int


class GoogleSheetsExportResponse(BaseModel):
    success: bool = True
    spreadsheet_id: str
    spreadsheet_url: str
    property_id: str
    start_date: str
    end_date: str
    synced_at: str
    reports: list[GoogleSheetsReportExportResult]