import logging

import typer

from src.config.dates import ResolvedDateRange, resolve_date_range
from src.mcp.run_report_adapter import McpRunReportError

from src.reports.events_by_name import run_and_save_events_by_name
from src.reports.gmv_by_channel import run_and_save_gmv_by_source
from src.reports.sessions_by_channel import run_and_save_sessions_by_source

logger = logging.getLogger(__name__)

report_app = typer.Typer(help="Fetch GA4 reports and export JSON to output/.")


def _resolve_range(
    start_date: str | None,
    end_date: str | None,
    preset: str | None,
):
    try:
        return resolve_date_range(start_date, end_date, preset=preset)
    except ValueError as exc:
        typer.echo(f"Invalid date parameters: {exc}")
        raise typer.Exit(code=1) from exc


def _run_gmv(date_range: ResolvedDateRange) -> None:
    try:
        payload, path = run_and_save_gmv_by_source(date_range)
    except McpRunReportError as exc:
        logger.exception("GMV report failed")
        typer.echo(f"Report failed: {exc}")
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        logger.exception("GMV report failed")
        typer.echo(f"Report failed: {exc}")
        raise typer.Exit(code=1) from exc

    typer.echo(f"Saved {len(payload['data'])} rows to {path}")
    if payload.get("currency"):
        typer.echo(f"Currency: {payload['currency']}")


def _run_sessions(date_range: ResolvedDateRange) -> None:
    try:
        payload, path = run_and_save_sessions_by_source(date_range)
    except McpRunReportError as exc:
        logger.exception("Sessions report failed")
        typer.echo(f"Report failed: {exc}")
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        logger.exception("Sessions report failed")
        typer.echo(f"Report failed: {exc}")
        raise typer.Exit(code=1) from exc

    typer.echo(f"Saved {len(payload['data'])} rows to {path}")


@report_app.command("gmv-by-source")
def gmv_by_source(
    start_date: str | None = typer.Option(
        None, "--start-date", help="YYYY-MM-DD or preset name"
    ),
    end_date: str | None = typer.Option(
        None, "--end-date", help="YYYY-MM-DD or preset name"
    ),
    preset: str | None = typer.Option(
        None,
        "--preset",
        help="yesterday | last-7-days | last-30-days | this-month",
    ),
):
    """Daily gross purchase revenue (GMV) by session source (MCP)."""
    _run_gmv(_resolve_range(start_date, end_date, preset))


@report_app.command("sessions-by-source")
def sessions_by_source(
    start_date: str | None = typer.Option(
        None, "--start-date", help="YYYY-MM-DD or preset name"
    ),
    end_date: str | None = typer.Option(
        None, "--end-date", help="YYYY-MM-DD or preset name"
    ),
    preset: str | None = typer.Option(
        None,
        "--preset",
        help="yesterday | last-7-days | last-30-days | this-month",
    ),
):
    """Daily sessions by session source (MCP)."""
    _run_sessions(_resolve_range(start_date, end_date, preset))


@report_app.command("gmv-by-channel", hidden=True)
def gmv_by_channel(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
    preset: str | None = typer.Option(None, "--preset"),
):
    """Deprecated alias for gmv-by-source."""
    typer.echo("Note: gmv-by-channel is deprecated; use report gmv-by-source.")
    _run_gmv(_resolve_range(start_date, end_date, preset))


@report_app.command("sessions-by-channel", hidden=True)
def sessions_by_channel(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
    preset: str | None = typer.Option(None, "--preset"),
):
    """Deprecated alias for sessions-by-source."""
    typer.echo("Note: sessions-by-channel is deprecated; use report sessions-by-source.")
    _run_sessions(_resolve_range(start_date, end_date, preset))


@report_app.command("events-by-name")
def events_by_name(
    start_date: str | None = typer.Option(
        None, "--start-date", help="YYYY-MM-DD or preset name"
    ),
    end_date: str | None = typer.Option(
        None, "--end-date", help="YYYY-MM-DD or preset name"
    ),
    preset: str | None = typer.Option(
        None,
        "--preset",
        help="yesterday | last-7-days | last-30-days | this-month",
    ),
):
    """GA4 Events report: metrics by event name (summary + daily)."""
    date_range = _resolve_range(start_date, end_date, preset)
    try:
        payload, path, count = run_and_save_events_by_name(date_range)
    except Exception as exc:
        logger.exception("Events report failed")
        typer.echo(f"Report failed: {exc}")
        raise typer.Exit(code=1) from exc

    typer.echo(f"Saved {count} events to {path}")
    if payload.get("currency"):
        typer.echo(f"Currency: {payload['currency']}")