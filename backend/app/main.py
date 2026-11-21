"""Điểm khởi động FastAPI.

Chạy dev (từ thư mục backend/):  uvicorn app.main:app --reload --port 8000
Tài liệu API tự sinh:            http://localhost:8000/docs
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import DataNotReadyError, InvalidParameterError
from app.core.logging import setup_logging

settings = get_settings()
setup_logging(settings.log_level)
log = logging.getLogger("app")

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.include_router(api_router)


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    # Lỗi SQL/DB -> log đầy đủ ở terminal backend, trả 503 gọn cho frontend.
    log.exception("Lỗi database tại %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=503,
        content={"detail": "Database error", "error_type": exc.__class__.__name__},
    )


@app.exception_handler(DataNotReadyError)
async def data_not_ready_handler(request: Request, exc: DataNotReadyError) -> JSONResponse:
    # Thiếu dữ liệu (vd bảng gold.ml_* chưa có): 404 kèm gợi ý cách tạo dữ liệu.
    return JSONResponse(
        status_code=404,
        content={"detail": exc.message, "hint": exc.hint, "error_type": "DataNotReady"},
    )


@app.exception_handler(InvalidParameterError)
async def invalid_parameter_handler(request: Request, exc: InvalidParameterError) -> JSONResponse:
    return JSONResponse(
        status_code=422, content={"detail": str(exc), "error_type": "InvalidParameter"}
    )
