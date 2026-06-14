from fastapi import APIRouter, Body, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from app.core.logging_config import setup_logging, get_request_logger
from pydantic import BaseModel
from typing import Optional, Type, Dict, Any
from app.utils import build_api_response, make_json_response
import os, uuid, json, time, traceback


logger = setup_logging()
router = APIRouter()


async def process_operation(param, payload, file, operation_id, req_logger):
    """백그라운드에서 실행되는 비동기 처리 함수"""
    from app.operate.operate_service import operate_run
    
    start_time = time.time()
    
    try:
        req_logger.info(f"[BACKGROUND] Processing started | file_included={bool(file)}")
        
        result = await operate_run(param, payload, **({"file": file} if file else {}))
        
        elapsed_time = time.time() - start_time
        result_summary = {
            "keys": list(result.keys()) if result else [],
            "spending_time": result.get("spending_time(s)", "N/A") if result else None,
        }
        
        req_logger.info(
            f"[BACKGROUND] REQUEST_COMPLETED | "
            f"status=200 | "
            f"elapsed_time={elapsed_time:.2f}s | "
            f"result_summary={json.dumps(result_summary, ensure_ascii=False)}"
        )
    except HTTPException as e:
        elapsed_time = time.time() - start_time
        req_logger.error(
            f"[BACKGROUND] REQUEST_FAILED | "
            f"status={e.status_code} | "
            f"error_code={e.detail.get('error_code', '-')} | "
            f"message={e.detail.get('message', '-')} | "
            f"elapsed_time={elapsed_time:.2f}s"
        )
    except Exception as e:
        elapsed_time = time.time() - start_time
        req_logger.exception(
            f"[BACKGROUND] REQUEST_FAILED | "
            f"status=500 | "
            f"error_type={type(e).__name__} | "
            f"elapsed_time={elapsed_time:.2f}s | "
            f"traceback={traceback.format_exc()}"
        )


async def handle_request(
    request_cls: Type[BaseModel],
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    *,
    file: Optional[Any] = None,
):
    """요청 파라미터 검증 + 로깅 + 비동기 서비스 실행"""
    operation_id = uuid.uuid4().hex
    req_logger = get_request_logger(
        operation_id,
        payload.get("user_id"),
        payload.get("test"),
        request_cls.__name__,
    )

    # 요청 정보 로깅
    payload_keys = list(payload.keys())
    payload_info = {
        "user_id": payload.get("user_id"),
        "test": payload.get("test"),
        "has_model": "model" in payload,
        "has_file": "file" in payload,
        "payload_keys": payload_keys,
    }
    req_logger.info(f"[REQUEST] Received | payload_info={json.dumps(payload_info, ensure_ascii=False)}")

    # ----------------------------------------------------------------------
    # 1️⃣ Pydantic Payload 검증
    # ----------------------------------------------------------------------
    try:
        param = request_cls(**payload)
        req_logger.info(f"[VALIDATION] Passed | model={request_cls.__name__}")
    except Exception as e:
        validation_errors = e.errors() if hasattr(e, 'errors') else str(e)
        req_logger.error(
            f"[VALIDATION] Failed | "
            f"model={request_cls.__name__} | "
            f"errors={json.dumps(validation_errors, ensure_ascii=False, default=str)}"
        )
        raise HTTPException(
            status_code=422,
            detail=make_json_response(
                422, "VALIDATION_ERROR", "Request validation failed", e.errors()
            ),
        )

    # 비동기 처리 시작
    req_logger.info(f"[ASYNC] Starting background processing | operation_id={operation_id}")

    # 백그라운드에서 실제 작업 실행
    background_tasks.add_task(
        process_operation,
        param=param,
        payload=payload,
        file=file,
        operation_id=operation_id,
        req_logger=req_logger,
    )

    response_data = build_api_response(
        202,
        "A001",
        "Processing",
        data={"message": "Request accepted and being processed"},
        operation_id=operation_id,
    )

    req_logger.info(f"[RESPONSE] Returning 202 Accepted | operation_id={operation_id}")

    return JSONResponse(
        status_code=202,
        content=response_data,
        headers={"X-Operation-Id": operation_id},
    )


# ----------------------------------------------------------------------
# ✅ 예시 라우터 (비동기 처리)
# ----------------------------------------------------------------------
@router.post("/~test")
async def run_test(
    payload: dict = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    from app.models.test_model import _testRequest
    return await handle_request(_testRequest, payload, background_tasks)


@router.post("/~file")
async def run_test_file(
    payload: dict = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    from app.models.test_model import _testRequest
    return await handle_request(
        _testRequest,
        payload,
        background_tasks,
        file=payload.get("file"),
    )
