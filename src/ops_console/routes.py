from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

STATIC_DIR = Path(__file__).resolve().parent / "static"


def register_ops_console_routes(application: FastAPI) -> None:
    """Mount JWT ops console at /ops (static; all data via authenticated /api/v1)."""

    @application.get("/ops")
    @application.get("/ops/")
    def ops_index():
        return FileResponse(STATIC_DIR / "index.html")

    application.mount(
        "/ops/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="ops_console_static",
    )