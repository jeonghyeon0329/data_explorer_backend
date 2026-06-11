from fastapi import HTTPException
from app.utils import make_json_response, Console, FileManager
import importlib
import datetime
import asyncio
import inspect


console = Console()


async def operate_run(operate_parameter, payload, file=None):
    """
    동적 모델 오퍼레이션 실행 함수
    - 파일 저장
    - 동적 모듈 로드 및 프로세서 인스턴스 실행
    - 단계별(generation, parsing) 처리
    """
    console.log("")
    start_time = datetime.datetime.now()
    console.log(f"start_time : {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # ------------------------------------------------------------------
    # 1️⃣ 파일 저장
    # ------------------------------------------------------------------
    try:
        file_manager = FileManager(
            payload.get("user_id"),
            payload.get("test")  # affiliation 대신 test 필드 사용
        )
        if file:
            await file_manager.save_file_to_dataset(file)

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=make_json_response(
                422, "B001", "Failed to save data", str(e)
            )
        )
    # ------------------------------------------------------------------
    # 2️⃣ 모델별 Processor 로드 및 실행
    # ------------------------------------------------------------------
    result = None
    service_results = {}  # 서비스 간 결과 전달을 위한 context
    
    for model_type, model_kind in operate_parameter.model.items():
        module_path = f"app.services.{model_kind}_operation"
        class_name = f"{model_kind.capitalize()}Processor"

        # ✅ 모듈 로드
        try:
            loaded_module = importlib.import_module(module_path)
            processor_class = getattr(loaded_module, class_name, None)
            if processor_class is None:
                raise Exception(f"Can't find {model_type}: {model_kind}")
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=make_json_response(
                    404, "B002", "Failed to find module", str(e)
                )
            )

        # ✅ 인스턴스 생성
        try:
            processor = processor_class(file_manager, operate_parameter)
            processor.service_context = service_results  # 이전 서비스 결과 전달
            if not processor.condition["success"]:
                raise Exception(
                    f"{model_type}:{model_kind}, "
                    f"condition: {processor.condition['error_message']}"
                )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=make_json_response(
                    500, "B003", "Failed to operate condition", str(e)
                )
            )

        # ✅ 처리 단계 정의
        steps = [
            ("generation", processor.generation),
            ("parsing", processor.parsing),
        ]

        async def execute_stage(func):
            if inspect.iscoroutinefunction(func):
                return await func()
            result = await asyncio.to_thread(func)
            return result

        # ✅ 단계별 실행
        for stage_name, step_func in steps:
            try:
                console.log(f"{model_kind} : {stage_name}")
                result = await execute_stage(step_func)
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=make_json_response(
                        500,
                        "B005",
                        "Failed to operate processor structure",
                        f"{model_type}:{model_kind}:{stage_name}:{str(e)}"
                    )
                )
        
        # 서비스 결과 저장
        service_results[model_kind] = result

    # ------------------------------------------------------------------
    # 3️⃣ 종료 시각 및 결과 리턴
    # ------------------------------------------------------------------
    end_time = datetime.datetime.now()
    console.log(f"end_time : {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    console.log("")

    return {
        "spending_time(s)": (end_time - start_time).total_seconds(),
        "result": result,
        "services": service_results,  # 모든 서비스 결과 반환
    }
