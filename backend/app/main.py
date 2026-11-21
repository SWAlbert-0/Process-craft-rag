import logging
import uuid

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.conversations import router as conversations_router
from app.api.documents import router as documents_router
from app.api.documents import task_router
from app.api.settings import router as settings_router
from app.config import get_settings
from app.db import SessionLocal
from app.errors import AppError
from app.services.vector_store import QdrantStore

logger = logging.getLogger(__name__)
settings = get_settings()
app = FastAPI(title="Process Craft RAG API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))[:100]
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": request.state.request_id,
                "details": exc.details,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, _exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "请求参数不符合接口要求",
                "request_id": request.state.request_id,
                "details": None,
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled request error", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "服务处理失败，请稍后重试",
                "request_id": request.state.request_id,
                "details": None,
            }
        },
    )


@app.get("/api/v1/health", tags=["health"])
async def health() -> JSONResponse:
    database_ready = False
    qdrant_ready = False
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            database_ready = True
    except Exception:
        logger.exception("Database readiness check failed")
    store = QdrantStore(settings.qdrant_url)
    try:
        qdrant_ready = await store.ready()
    finally:
        await store.close()
    ready = database_ready and qdrant_ready
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "status": "ready" if ready else "not_ready",
            "database": database_ready,
            "qdrant": qdrant_ready,
        },
    )


app.include_router(documents_router, prefix="/api/v1")
app.include_router(task_router, prefix="/api/v1")
app.include_router(conversations_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")


def run() -> None:
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
