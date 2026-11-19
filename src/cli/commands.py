import logging

import typer

from src.config.dates import resolve_date_range
from src.reports.events_by_name import run_and_save_events_by_name
from src.reports.gmv_by_channel import run_and_save_gmv_by_channel
from src.reports.sessions_by_channel import run_and_save_sessions_by_channel

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


@report_app.command("gmv-by-channel")
def gmv_by_channel(
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
    """Daily gross purchase revenue (GMV) by default channel group."""
    date_range = _resolve_range(start_date, end_date, preset)
    try:
        payload, path = run_and_save_gmv_by_channel(date_range)
    except Exception as exc:
        logger.exception("GMV report failed")
        typer.echo(f"Report failed: {exc}")
        raise typer.Exit(code=1) from exc

    typer.echo(f"Saved {len(payload['data'])} rows to {path}")
    if payload.get("currency"):
        typer.echo(f"Currency: {payload['currency']}")


@report_app.command("sessions-by-channel")
def sessions_by_channel(
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
    """Daily sessions by default channel group."""
    date_range = _resolve_range(start_date, end_date, preset)
    try:
        payload, path = run_and_save_sessions_by_channel(date_range)
    except Exception as exc:
        logger.exception("Sessions report failed")
        typer.echo(f"Report failed: {exc}")
        raise typer.Exit(code=1) from exc

    typer.echo(f"Saved {len(payload['data'])} rows to {path}")


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