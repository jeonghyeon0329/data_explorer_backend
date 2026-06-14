import json
import uuid
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.dataset_model import Dataset, DatasetColumn
from app.models.user_model import User
from app.utils import raise_http

UPLOAD_ROOT = Path("uploads")
ALLOWED_TYPES = {"csv", "xlsx", "json"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
VALID_OPS = {"eq", "ne", "gt", "lt", "gte", "lte", "contains"}


# ── 내부 헬퍼 ──────────────────────────────────────────────────

def _get_file_type(filename: str) -> str:
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in ALLOWED_TYPES:
        raise_http(400, "D001", f"Unsupported file type. Allowed: csv, xlsx, json")
    return ext


def read_file(path: Path, file_type: str) -> pd.DataFrame:
    try:
        if file_type == "csv":
            return pd.read_csv(path, encoding="utf-8-sig")
        if file_type == "xlsx":
            return pd.read_excel(path, engine="openpyxl")
        if file_type == "json":
            return pd.read_json(path)
    except Exception as e:
        raise_http(400, "D002", f"File parsing failed: {e}")


def dtype_label(dtype) -> str:
    name = str(dtype)
    if "int" in name:   return "int"
    if "float" in name: return "float"
    if "bool" in name:  return "bool"
    if "datetime" in name: return "datetime"
    return "str"


def check_access(dataset: Optional[Dataset], user: User) -> None:
    if dataset is None:
        raise_http(404, "D101", "Dataset not found")
    if dataset.user_id != user.id and not dataset.is_public and user.role != "admin":
        raise_http(403, "D102", "Access denied")


def _build_column_metas(df: pd.DataFrame, dataset_id: int) -> list:
    metas = []
    for order, col in enumerate(df.columns):
        series = df[col]
        null_count = int(series.isna().sum())
        unique_count = int(series.nunique(dropna=True))
        dlabel = dtype_label(series.dtype)

        min_val = max_val = None
        try:
            if dlabel in ("int", "float", "datetime"):
                min_val = str(series.dropna().min())
                max_val = str(series.dropna().max())
        except Exception:
            pass

        try:
            sample_json = json.dumps(
                [str(s) for s in series.dropna().head(5).tolist()],
                ensure_ascii=False,
            )
        except Exception:
            sample_json = "[]"

        metas.append(DatasetColumn(
            dataset_id=dataset_id,
            column_name=str(col),
            column_order=order,
            dtype=dlabel,
            null_count=null_count,
            unique_count=unique_count,
            min_value=min_val,
            max_value=max_val,
            sample_values=sample_json,
        ))
    return metas


# ── Public API ─────────────────────────────────────────────────

async def create_dataset(
    db: Session,
    user: User,
    file: UploadFile,
    name: Optional[str],
    description: Optional[str],
    is_public: bool,
) -> dict:
    file_type = _get_file_type(file.filename)
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise_http(413, "D003", "File size exceeds 50MB limit")

    user_dir = UPLOAD_ROOT / str(user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    storage_path = user_dir / f"{uuid.uuid4().hex}.{file_type}"
    storage_path.write_bytes(content)

    df = read_file(storage_path, file_type)
    dataset_name = (name or "").strip() or Path(file.filename).stem

    dataset = Dataset(
        user_id=user.id,
        name=dataset_name,
        description=description,
        file_type=file_type,
        original_filename=file.filename,
        file_size=len(content),
        row_count=len(df),
        column_count=len(df.columns),
        storage_path=str(storage_path),
        is_public=is_public,
    )
    db.add(dataset)
    db.flush()

    col_metas = _build_column_metas(df, dataset.id)
    for cm in col_metas:
        db.add(cm)

    return {
        "dataset_id": dataset.id,
        "name": dataset.name,
        "file_type": dataset.file_type,
        "row_count": dataset.row_count,
        "column_count": dataset.column_count,
        "columns": [
            {"name": cm.column_name, "dtype": cm.dtype, "null_count": cm.null_count}
            for cm in col_metas
        ],
    }


def list_datasets(
    db: Session,
    user: User,
    mine: bool,
    page: int,
    size: int,
    q: Optional[str],
) -> dict:
    query = db.query(Dataset)
    if mine:
        query = query.filter(Dataset.user_id == user.id)
    else:
        query = query.filter(
            (Dataset.user_id == user.id) | (Dataset.is_public == True)
        )
    if q:
        query = query.filter(Dataset.name.ilike(f"%{q}%"))

    total = query.count()
    items = (
        query.order_by(Dataset.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [
            {
                "id": d.id,
                "name": d.name,
                "file_type": d.file_type,
                "row_count": d.row_count,
                "column_count": d.column_count,
                "is_public": d.is_public,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in items
        ],
    }


def get_dataset(db: Session, dataset_id: int, user: User) -> dict:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    check_access(dataset, user)

    cols = (
        db.query(DatasetColumn)
        .filter(DatasetColumn.dataset_id == dataset_id)
        .order_by(DatasetColumn.column_order)
        .all()
    )
    return {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "file_type": dataset.file_type,
        "original_filename": dataset.original_filename,
        "file_size": dataset.file_size,
        "row_count": dataset.row_count,
        "column_count": dataset.column_count,
        "is_public": dataset.is_public,
        "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
        "updated_at": dataset.updated_at.isoformat() if dataset.updated_at else None,
        "columns": [
            {
                "name": c.column_name,
                "order": c.column_order,
                "dtype": c.dtype,
                "null_count": c.null_count,
                "unique_count": c.unique_count,
                "min_value": c.min_value,
                "max_value": c.max_value,
                "sample_values": json.loads(c.sample_values) if c.sample_values else [],
            }
            for c in cols
        ],
    }


def update_dataset(
    db: Session,
    dataset_id: int,
    user: User,
    name: Optional[str],
    description: Optional[str],
    is_public: Optional[bool],
) -> dict:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if dataset is None:
        raise_http(404, "D101", "Dataset not found")
    if dataset.user_id != user.id and user.role != "admin":
        raise_http(403, "D102", "Access denied")

    if name is not None:
        dataset.name = name.strip() or dataset.name
    if description is not None:
        dataset.description = description
    if is_public is not None:
        dataset.is_public = is_public

    return {"id": dataset.id, "name": dataset.name, "is_public": dataset.is_public}


def delete_dataset(db: Session, dataset_id: int, user: User) -> None:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if dataset is None:
        raise_http(404, "D101", "Dataset not found")
    if dataset.user_id != user.id and user.role != "admin":
        raise_http(403, "D102", "Access denied")

    path = Path(dataset.storage_path)
    if path.exists():
        path.unlink()

    db.delete(dataset)


def preview_dataset(
    db: Session,
    dataset_id: int,
    user: User,
    page: int,
    size: int,
    sort_by: Optional[str],
    sort_dir: str,
    filter_json: Optional[str],
) -> dict:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    check_access(dataset, user)

    df = read_file(Path(dataset.storage_path), dataset.file_type)

    if filter_json:
        try:
            filters = json.loads(filter_json)
            if not isinstance(filters, list):
                filters = [filters]
        except Exception:
            raise_http(400, "D010", "Invalid filter JSON")

        for f in filters:
            col, op, val = f.get("col"), f.get("op"), f.get("val")
            if col not in df.columns:
                raise_http(400, "D011", f"Column not found: {col}")
            if op not in VALID_OPS:
                raise_http(400, "D012", f"Invalid operator: {op}")
            try:
                if op == "eq":       df = df[df[col] == val]
                elif op == "ne":     df = df[df[col] != val]
                elif op == "gt":     df = df[df[col] > float(val)]
                elif op == "lt":     df = df[df[col] < float(val)]
                elif op == "gte":    df = df[df[col] >= float(val)]
                elif op == "lte":    df = df[df[col] <= float(val)]
                elif op == "contains":
                    df = df[df[col].astype(str).str.contains(str(val), case=False, na=False)]
            except Exception:
                raise_http(400, "D013", f"Filter error on column: {col}")

    if sort_by and sort_by in df.columns:
        df = df.sort_values(by=sort_by, ascending=(sort_dir.lower() != "desc"))

    total_rows = len(df)
    start = (page - 1) * size
    page_df = df.iloc[start: start + size]

    rows = []
    for _, row in page_df.iterrows():
        rows.append([
            None if pd.isna(v) else (v.isoformat() if hasattr(v, "isoformat") else v)
            for v in row
        ])

    return {
        "total_rows": total_rows,
        "page": page,
        "size": size,
        "columns": list(df.columns),
        "rows": rows,
    }


def get_column_stats(db: Session, dataset_id: int, col_name: str, user: User) -> dict:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    check_access(dataset, user)

    df = read_file(Path(dataset.storage_path), dataset.file_type)
    if col_name not in df.columns:
        raise_http(404, "D201", f"Column not found: {col_name}")

    series = df[col_name]
    dlabel = dtype_label(series.dtype)
    stats: dict = {
        "column": col_name,
        "dtype": dlabel,
        "total_count": len(series),
        "null_count": int(series.isna().sum()),
        "unique_count": int(series.nunique(dropna=True)),
        "sample_values": [str(v) for v in series.dropna().head(10).tolist()],
    }

    if dlabel in ("int", "float"):
        numeric = series.dropna()
        stats.update({
            "min": float(numeric.min()),
            "max": float(numeric.max()),
            "mean": round(float(numeric.mean()), 6),
            "median": float(numeric.median()),
            "std": round(float(numeric.std()), 6),
        })
    elif dlabel == "str":
        top = series.value_counts().head(10)
        stats["top_values"] = [
            {"value": str(k), "count": int(v)} for k, v in top.items()
        ]

    return stats
