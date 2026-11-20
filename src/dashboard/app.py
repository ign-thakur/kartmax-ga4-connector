from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.router import api_v1_router
from src.config.app_profile import is_dashboard_enabled, is_ops_console_enabled
from src.ops_console.routes import register_ops_console_routes
from src.dashboard.channel_service import get_channel_dashboard
from src.dashboard.events_service import get_events_view
from src.dashboard.repository import get_available_range, list_reports, load_report

STATIC_DIR = Path(__file__).resolve().parent / "static"


def _register_dashboard_routes(application: FastAPI) -> None:
    @application.get("/api/range")
    def api_available_range():
        return get_available_range()

    @application.get("/api/dashboard")
    def api_dashboard(
        start_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
        end_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    ):
        try:
            return get_channel_dashboard(start_date, end_date)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @application.get("/api/events")
    def api_events(
        start_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
        end_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
        search: str = Query("purchase", min_length=0, max_length=128),
    ):
        try:
            return get_events_view(start_date, end_date, search=search)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @application.get("/events")
    def events_page():
        return FileResponse(STATIC_DIR / "events.html")

    @application.get("/api/reports")
    def api_list_reports():
        return {"reports": list_reports()}

    @application.get("/api/reports/{filename}")
    def api_get_report(filename: str):
        try:
            return load_report(filename)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @application.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    application.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def create_app() -> FastAPI:
    application = FastAPI(title="KartmaX GA4 Report Viewer", version="0.4.0")
    application.include_router(api_v1_router)
    if is_dashboard_enabled():
        _register_dashboard_routes(application)
    if is_ops_console_enabled():
        register_ops_console_routes(application)
    return application


app = create_app()