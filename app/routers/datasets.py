from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from pydantic import BaseModel

from app.dependencies.auth import get_current_user
from app.models.user_model import User
from app.services import chart_service, dataset_service
from app.utils import build_api_response

router = APIRouter()


class DatasetUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None


class ChartCreateRequest(BaseModel):
    title: str
    chart_type: str
    x_column: Optional[str] = None
    y_column: Optional[str] = None
    config: Optional[dict] = None


# ── Dataset CRUD ───────────────────────────────────────────────

@router.post("/", status_code=201)
async def upload_dataset(
    request: Request,
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    is_public: bool = Form(False),
    user: User = Depends(get_current_user),
):
    data = await dataset_service.create_dataset(
        request.state.db, user, file, name, description, is_public
    )
    return build_api_response(201, "A001", "Dataset uploaded successfully", data=data)


@router.get("/")
async def list_datasets(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    mine: bool = Query(True),
    q: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
):
    data = dataset_service.list_datasets(request.state.db, user, mine, page, size, q)
    return build_api_response(200, "A001", "OK", data=data)


@router.get("/{dataset_id}")
async def get_dataset(
    dataset_id: int,
    request: Request,
    user: User = Depends(get_current_user),
):
    data = dataset_service.get_dataset(request.state.db, dataset_id, user)
    return build_api_response(200, "A001", "OK", data=data)


@router.patch("/{dataset_id}")
async def update_dataset(
    dataset_id: int,
    body: DatasetUpdateRequest,
    request: Request,
    user: User = Depends(get_current_user),
):
    data = dataset_service.update_dataset(
        request.state.db, dataset_id, user, body.name, body.description, body.is_public
    )
    return build_api_response(200, "A001", "Dataset updated", data=data)


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: int,
    request: Request,
    user: User = Depends(get_current_user),
):
    dataset_service.delete_dataset(request.state.db, dataset_id, user)
    return build_api_response(200, "A001", "Dataset deleted")


# ── Preview & Column Stats ─────────────────────────────────────

@router.get("/{dataset_id}/preview")
async def preview_dataset(
    dataset_id: int,
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    sort_by: Optional[str] = Query(None),
    sort_dir: str = Query("asc"),
    filter: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
):
    data = dataset_service.preview_dataset(
        request.state.db, dataset_id, user, page, size, sort_by, sort_dir, filter
    )
    return build_api_response(200, "A001", "OK", data=data)


@router.get("/{dataset_id}/columns/{col_name}")
async def get_column_stats(
    dataset_id: int,
    col_name: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    data = dataset_service.get_column_stats(request.state.db, dataset_id, col_name, user)
    return build_api_response(200, "A001", "OK", data=data)


# ── Charts ─────────────────────────────────────────────────────

@router.post("/{dataset_id}/charts/", status_code=201)
async def create_chart(
    dataset_id: int,
    body: ChartCreateRequest,
    request: Request,
    user: User = Depends(get_current_user),
):
    data = chart_service.create_chart(
        request.state.db, dataset_id, user,
        body.title, body.chart_type, body.x_column, body.y_column, body.config,
    )
    return build_api_response(201, "A001", "Chart created", data=data)


@router.get("/{dataset_id}/charts/")
async def list_charts(
    dataset_id: int,
    request: Request,
    user: User = Depends(get_current_user),
):
    data = chart_service.list_charts(request.state.db, dataset_id, user)
    return build_api_response(200, "A001", "OK", data={"charts": data})


@router.get("/{dataset_id}/charts/{chart_id}")
async def get_chart_data(
    dataset_id: int,
    chart_id: int,
    request: Request,
    user: User = Depends(get_current_user),
):
    data = chart_service.get_chart_data(request.state.db, dataset_id, chart_id, user)
    return build_api_response(200, "A001", "OK", data=data)


@router.delete("/{dataset_id}/charts/{chart_id}")
async def delete_chart(
    dataset_id: int,
    chart_id: int,
    request: Request,
    user: User = Depends(get_current_user),
):
    chart_service.delete_chart(request.state.db, dataset_id, chart_id, user)
    return build_api_response(200, "A001", "Chart deleted")
