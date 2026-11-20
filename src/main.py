
import typer

from src.auth.ga4_client import test_ga4_connection
from src.cli.commands import report_app
from src.config.logging_config import configure_logging
from src.mcp.client import (
    RUN_REPORT_TOOL,
    McpClientError,
    run_mcp_connectivity_check,
    run_mcp_run_report_smoke_test,
)

configure_logging()

app = typer.Typer(
    name="kartmax-ga4",
    help="KartmaX Google Analytics Connector",
)
app.add_typer(report_app, name="report")


@app.callback()
def main():
    """KartmaX GA4 CLI."""
    pass


@app.command("mcp-status")
def mcp_status():
    """Test connectivity to the Google Analytics MCP server (HTTP)."""
    try:
        result = run_mcp_connectivity_check()
    except McpClientError as error:
        typer.echo("MCP Connection: FAILED")
        typer.echo(f"Error: {error}")
        raise typer.Exit(code=1) from error

    if not result.connected:
        typer.echo("MCP Connection: FAILED")
        typer.echo(f"Server: {result.server_url}")
        typer.echo(f"Error: {result.error_message}")
        raise typer.Exit(code=1)

    typer.echo("MCP Connection: SUCCESS")
    typer.echo(f"Server: {result.server_url}")
    typer.echo(f"Tools listed: {len(result.tool_names)}")
    if result.run_report_available:
        typer.echo(f"{RUN_REPORT_TOOL}: available")
    else:
        typer.echo(f"{RUN_REPORT_TOOL}: NOT FOUND")
        if result.error_message:
            typer.echo(f"Detail: {result.error_message}")
        raise typer.Exit(code=1)


@app.command("mcp-run-report-smoke")
def mcp_run_report_smoke():
    """Call MCP run_report (sessions, yesterday) using the service account Bearer token."""
    result = run_mcp_run_report_smoke_test()
    if not result.ok:
        typer.echo("MCP run_report: FAILED")
        typer.echo(f"Property: {result.property_id}")
        typer.echo(f"Error: {result.error_message}")
        raise typer.Exit(code=1)

    typer.echo("MCP run_report: SUCCESS")
    typer.echo(f"Property: {result.property_id}")
    typer.echo(f"Rows: {result.row_count}")
    if result.sessions_value is not None:
        typer.echo(f"Sessions (yesterday): {result.sessions_value}")
    typer.echo(result.summary)


@app.command()
def status():
    """Test Google Analytics connectivity."""
    try:
        response = test_ga4_connection()

        typer.echo("GA4 Connection: SUCCESS")
        typer.echo(f"Report rows received: {len(response.rows)}")

        if response.rows:
            typer.echo(
                f"Sessions yesterday: {response.rows[0].metric_values[0].value}"
            )

    except Exception as error:
        typer.echo("GA4 Connection: FAILED")
        typer.echo(f"Error: {error}")
        raise typer.Exit(code=1)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind address"),
    port: int = typer.Option(8080, "--port", help="Port"),
):
    """Open a local web UI to browse JSON reports in output/."""
    try:
        import uvicorn

        from src.dashboard.app import app as web_app

        typer.echo(f"Dashboard: http://{host}:{port}/")
        typer.echo("Press Ctrl+C to stop.")
        uvicorn.run(web_app, host=host, port=port, log_level="info")
    except ImportError as exc:
        typer.echo("Missing dependencies. Install with: pip install fastapi uvicorn")
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    app()