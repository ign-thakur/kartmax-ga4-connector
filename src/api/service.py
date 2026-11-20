"""Orchestrate MCP source reports for REST responses."""

from __future__ import annotations

from typing import Any

from src.api.schemas import (
    GmvSourceRow,
    HealthMcpStatus,
    HealthResponse,
    SessionsSourceRow,
    SourceReportResponse,
)
from src.api.validation import validate_property_id, validate_report_date_range
from src.config.dates import ResolvedDateRange
from src.mcp.client import check_mcp_connectivity, run_mcp_connectivity_check
from src.reports.gmv_by_channel import (
    METRIC_KEY as GMV_METRIC_KEY,
    REPORT_TYPE as GMV_REPORT_TYPE,
    fetch_gmv_by_source,
)
from src.reports.sessions_by_channel import (
    METRIC_KEY as SESSIONS_METRIC_KEY,
    REPORT_TYPE as SESSIONS_REPORT_TYPE,
    fetch_sessions_by_source,
)


def _date_range(start_date: str, end_date: str) -> ResolvedDateRange:
    return ResolvedDateRange(
        start_date=start_date,
        end_date=end_date,
        label_start=start_date,
        label_end=end_date,
    )


def _numeric_rows(payload: dict[str, Any], metric_key: str) -> list[dict[str, Any]]:
    row_model = GmvSourceRow if metric_key == GMV_METRIC_KEY else SessionsSourceRow
    rows: list[dict[str, Any]] = []
    for row in payload.get("data") or []:
        raw = row.get(metric_key)
        if raw is None:
            raise ValueError(f"Row missing metric '{metric_key}'.")
        model = row_model.model_validate(
            {
                "date": row["date"],
                "source": row["source"],
                metric_key: float(raw),
            }
        )
        rows.append(model.model_dump())
    return rows


def fetch_gmv_report_for_api(
    *,
    property_id: str,
    start_date: str,
    end_date: str,
) -> SourceReportResponse:
    pid = validate_property_id(property_id)
    start, end = validate_report_date_range(start_date, end_date)
    payload = fetch_gmv_by_source(
        _date_range(start, end),
        property_id=pid,
        allow_empty=True,
    )
    return SourceReportResponse(
        report_type=GMV_REPORT_TYPE,
        property_id=str(payload["property_id"]),
        currency=payload.get("currency"),
        start_date=payload["start_date"],
        end_date=payload["end_date"],
        data=_numeric_rows(payload, GMV_METRIC_KEY),
    )


def fetch_sessions_report_for_api(
    *,
    property_id: str,
    start_date: str,
    end_date: str,
) -> SourceReportResponse:
    pid = validate_property_id(property_id)
    start, end = validate_report_date_range(start_date, end_date)
    payload = fetch_sessions_by_source(
        _date_range(start, end),
        property_id=pid,
        allow_empty=True,
    )
    return SourceReportResponse(
        report_type=SESSIONS_REPORT_TYPE,
        property_id=str(payload["property_id"]),
        currency=payload.get("currency"),
        start_date=payload["start_date"],
        end_date=payload["end_date"],
        data=_numeric_rows(payload, SESSIONS_METRIC_KEY),
    )


def build_health_response() -> HealthResponse:
    result = run_mcp_connectivity_check()
    connector = "ok" if result.connected else "degraded"
    status = "ok" if result.ok else "degraded"
    return HealthResponse(
        status=status,
        connector=connector,
        mcp=HealthMcpStatus(
            connected=result.connected,
            run_report_available=result.run_report_available,
            error_message=result.error_message,
        ),
    )


async def build_health_response_async() -> HealthResponse:
    result = await check_mcp_connectivity()
    connector = "ok" if result.connected else "degraded"
    status = "ok" if result.ok else "degraded"
    return HealthResponse(
        status=status,
        connector=connector,
        mcp=HealthMcpStatus(
            connected=result.connected,
            run_report_available=result.run_report_available,
            error_message=result.error_message,
        ),
    )