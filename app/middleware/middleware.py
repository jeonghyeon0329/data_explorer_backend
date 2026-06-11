from fastapi import Request, Response
from fastapi.responses import JSONResponse
from typing import Callable
from app.utils import build_api_response

# 허용된 IP 및 URL prefix 설정
ALLOWED_IPS = {"127.0.0.1", "localhost", "testclient"}
ALLOWED_PREFIXES = {"/items"}


async def connection_context(request: Request, call_next: Callable[[Request], Response]) -> Response:
    """요청마다 DB/MinIO 클라이언트를 request.state에 주입합니다."""
    request.state.db_client = getattr(request.app.state, "db_client", None)
    request.state.storage_client = getattr(request.app.state, "storage_client", None)
    request.state.db = None

    if request.state.db_client is not None and hasattr(request.state.db_client, "connect"):
        try:
            request.state.db = request.state.db_client.connect()
        except Exception as exc:
            return JSONResponse(
                status_code=500,
                content=build_api_response(
                    500,
                    "DB_CONNECTION_ERROR",
                    "Failed to connect to the configured database.",
                    errors=str(exc),
                ),
            )

    try:
        response = await call_next(request)
        if request.state.db is not None and hasattr(request.state.db, "commit"):
            request.state.db.commit()
        return response
    except Exception:
        if request.state.db is not None and hasattr(request.state.db, "rollback"):
            request.state.db.rollback()
        raise
    finally:
        if request.state.db is not None and hasattr(request.state.db, "close"):
            request.state.db.close()


async def ip_access(request: Request, call_next: Callable[[Request], Response]) -> Response:
    """IP 및 경로 접근 제어 미들웨어"""

    client_ip = request.client.host
    path = request.url.path

    if client_ip not in ALLOWED_IPS:
        return JSONResponse(
            status_code=403,
            content=build_api_response(
                403,
                "C001",
                f"Access denied for IP: {client_ip}",
                errors=f"Access denied for IP: {client_ip}",
            ),
        )

    first_segment = "/" + path.lstrip("/").split("/", 1)[0]
    if first_segment not in ALLOWED_PREFIXES:
        return JSONResponse(
            status_code=404,
            content=build_api_response(
                404,
                "C002",
                f"Invalid API path: {path}",
                errors=f"Invalid API path: {path}",
            ),
        )

    return await call_next(request)


