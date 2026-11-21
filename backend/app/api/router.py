"""Gom tất cả router. Thêm endpoint mới: tạo file trong api/routes/ rồi include ở đây."""

from fastapi import APIRouter

from app.api.routes import cancellation, filters, forecast, health, kpi, pipeline, ranking, what_if

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(pipeline.router)
api_router.include_router(filters.router)
api_router.include_router(kpi.router)
api_router.include_router(cancellation.router)
api_router.include_router(forecast.router)
api_router.include_router(ranking.router)
api_router.include_router(what_if.router)
