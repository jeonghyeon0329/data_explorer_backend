from app.middleware.middleware import connection_context, ip_access
from app.routers import accounts, admin, datasets, items
from app.core.database import DatabaseConnector
from app.core.storage import MinioStorage
from app.models.user_model import Base
from app.models import dataset_model, chart_model  # noqa: F401 — Base.metadata 등록
from settings import settings

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.utils import build_api_response


def create_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.middleware("http")(connection_context)
    app.middleware("http")(ip_access)

    app.include_router(items.router,    prefix="/items",    tags=["items"])
    app.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
    app.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
    app.include_router(admin.router,    prefix="/admin",    tags=["admin"])

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        detail = exc.detail
        if isinstance(detail, dict) and detail.get("status_code"):
            content = detail
        else:
            content = build_api_response(exc.status_code, "HTTP_ERROR", str(detail), errors=detail)
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=build_api_response(422, "VALIDATION_ERROR", "Request validation failed", errors=exc.errors()),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content=build_api_response(500, "A999", "Unexpected internal error", errors=str(exc)),
        )

    if settings.db_user and settings.db_password:
        connector = DatabaseConnector(settings.db_url)
        app.state.db_client = connector
        try:
            connector.test_connection()
            Base.metadata.create_all(bind=connector.engine)
            print("[INFO] Database connected and tables verified.")
        except Exception as exc:
            print(f"[WARN] Database connection failed at startup: {exc}")

    if settings.minio_endpoint and settings.minio_access_key and settings.minio_secret_key:
        try:
            app.state.storage_client = MinioStorage(
                endpoint=settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
        except Exception:
            app.state.storage_client = None

    return app


app = create_app()
