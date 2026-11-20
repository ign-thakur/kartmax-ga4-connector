from fastapi import APIRouter

from src.api.routes import auth, exports, health, reports

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth.router)
api_v1_router.include_router(exports.router)
api_v1_router.include_router(reports.router)
api_v1_router.include_router(health.router)