"""Gom tất cả router. Thêm endpoint mới: tạo file trong api/routes/ rồi include ở đây."""

from fastapi import APIRouter

from app.api.routes import health, pipeline

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(pipeline.router)
