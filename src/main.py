
import typer

from src.auth.ga4_client import test_ga4_connection
from src.cli.commands import report_app
from src.config.logging_config import configure_logging

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