from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.dependencies.auth import get_admin_user
from app.models.dataset_model import Dataset
from app.models.user_model import User
from app.utils import build_api_response, raise_http

router = APIRouter()


class UserUpdateRequest(BaseModel):
    role: Optional[str] = None      # user | admin
    is_active: Optional[bool] = None


# ── 사용자 관리 ────────────────────────────────────────────────

@router.get("/users/")
async def list_users(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None),
    admin: User = Depends(get_admin_user),
):
    db = request.state.db
    query = db.query(User)
    if q:
        query = query.filter(
            User.username.ilike(f"%{q}%") | User.email.ilike(f"%{q}%")
        )
    total = query.count()
    users = (
        query.order_by(User.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return build_api_response(200, "A001", "OK", data={
        "total": total,
        "page": page,
        "size": size,
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "name": u.name,
                "email": u.email,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    })


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int,
    body: UserUpdateRequest,
    request: Request,
    admin: User = Depends(get_admin_user),
):
    db = request.state.db
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise_http(404, "A404", "User not found")
    if user.id == admin.id:
        raise_http(400, "A400", "Cannot modify your own account via admin API")

    if body.role is not None:
        if body.role not in ("user", "admin"):
            raise_http(400, "A400", "Role must be 'user' or 'admin'")
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active

    return build_api_response(200, "A001", "User updated", data={
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
    })


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    admin: User = Depends(get_admin_user),
):
    db = request.state.db
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise_http(404, "A404", "User not found")
    if user.id == admin.id:
        raise_http(400, "A400", "Cannot delete your own account")
    db.delete(user)
    return build_api_response(200, "A001", "User deleted")


# ── 데이터셋 관리 ──────────────────────────────────────────────

@router.get("/datasets/")
async def list_all_datasets(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None),
    admin: User = Depends(get_admin_user),
):
    db = request.state.db
    query = db.query(Dataset)
    if q:
        query = query.filter(Dataset.name.ilike(f"%{q}%"))

    total = query.count()
    items = (
        query.order_by(Dataset.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    user_ids = {d.user_id for d in items}
    users = {
        u.id: u.username
        for u in db.query(User).filter(User.id.in_(user_ids)).all()
    }

    return build_api_response(200, "A001", "OK", data={
        "total": total,
        "page": page,
        "size": size,
        "items": [
            {
                "id": d.id,
                "name": d.name,
                "owner": users.get(d.user_id, "unknown"),
                "file_type": d.file_type,
                "row_count": d.row_count,
                "is_public": d.is_public,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in items
        ],
    })
