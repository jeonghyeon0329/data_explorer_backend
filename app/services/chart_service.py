import json
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.models.chart_model import Chart
from app.models.dataset_model import Dataset
from app.models.user_model import User
from app.services.dataset_service import check_access, read_file
from app.utils import raise_http

CHART_TYPES = {"bar", "line", "pie", "scatter", "histogram"}
AGG_FUNCS = {"sum", "mean", "count", "min", "max"}


def _load_df(db: Session, dataset_id: int, user: User) -> tuple:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    check_access(dataset, user)
    df = read_file(Path(dataset.storage_path), dataset.file_type)
    return dataset, df


def create_chart(
    db: Session,
    dataset_id: int,
    user: User,
    title: str,
    chart_type: str,
    x_column: Optional[str],
    y_column: Optional[str],
    config: Optional[dict],
) -> dict:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    check_access(dataset, user)

    if chart_type not in CHART_TYPES:
        raise_http(400, "C001", f"Invalid chart type. Allowed: {', '.join(sorted(CHART_TYPES))}")

    chart = Chart(
        dataset_id=dataset_id,
        user_id=user.id,
        title=title,
        chart_type=chart_type,
        x_column=x_column,
        y_column=y_column,
        config_json=json.dumps(config, ensure_ascii=False) if config else None,
    )
    db.add(chart)
    db.flush()

    return {
        "chart_id": chart.id,
        "title": chart.title,
        "chart_type": chart.chart_type,
        "x_column": chart.x_column,
        "y_column": chart.y_column,
    }


def list_charts(db: Session, dataset_id: int, user: User) -> list:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    check_access(dataset, user)

    charts = (
        db.query(Chart)
        .filter(Chart.dataset_id == dataset_id)
        .order_by(Chart.created_at.desc())
        .all()
    )
    return [
        {
            "chart_id": c.id,
            "title": c.title,
            "chart_type": c.chart_type,
            "x_column": c.x_column,
            "y_column": c.y_column,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in charts
    ]


def get_chart_data(db: Session, dataset_id: int, chart_id: int, user: User) -> dict:
    chart = (
        db.query(Chart)
        .filter(Chart.id == chart_id, Chart.dataset_id == dataset_id)
        .first()
    )
    if chart is None:
        raise_http(404, "C101", "Chart not found")

    _, df = _load_df(db, dataset_id, user)
    config = json.loads(chart.config_json) if chart.config_json else {}
    agg_func = config.get("aggregation", "sum")
    if agg_func not in AGG_FUNCS:
        agg_func = "sum"

    result: dict = {
        "chart_type": chart.chart_type,
        "title": chart.title,
        "x_column": chart.x_column,
        "y_column": chart.y_column,
        "config": config,
    }

    if chart.chart_type in ("bar", "line"):
        x_col, y_col = chart.x_column, chart.y_column
        if not x_col or not y_col:
            raise_http(400, "C102", "bar/line charts require x_column and y_column")
        if x_col not in df.columns or y_col not in df.columns:
            raise_http(400, "C103", "Column not found in dataset")

        grouped = df.groupby(x_col)[y_col]
        agg = getattr(grouped, agg_func)().head(50)

        result["labels"] = [str(k) for k in agg.index.tolist()]
        result["series"] = [{
            "name": y_col,
            "data": [round(float(v), 4) if pd.notna(v) else 0 for v in agg.values],
        }]

    elif chart.chart_type == "pie":
        x_col, y_col = chart.x_column, chart.y_column
        if not x_col or not y_col:
            raise_http(400, "C102", "pie charts require x_column and y_column")
        if x_col not in df.columns or y_col not in df.columns:
            raise_http(400, "C103", "Column not found in dataset")

        grouped = df.groupby(x_col)[y_col].sum().head(20)
        result["series"] = [
            {"name": str(k), "value": round(float(v), 4) if pd.notna(v) else 0}
            for k, v in grouped.items()
        ]

    elif chart.chart_type == "scatter":
        x_col, y_col = chart.x_column, chart.y_column
        if not x_col or not y_col:
            raise_http(400, "C102", "scatter charts require x_column and y_column")
        if x_col not in df.columns or y_col not in df.columns:
            raise_http(400, "C103", "Column not found in dataset")

        subset = df[[x_col, y_col]].dropna().head(1000)
        result["series"] = [{
            "name": f"{x_col} vs {y_col}",
            "data": [
                {"x": round(float(row[x_col]), 4), "y": round(float(row[y_col]), 4)}
                for _, row in subset.iterrows()
            ],
        }]

    elif chart.chart_type == "histogram":
        y_col = chart.y_column
        if not y_col:
            raise_http(400, "C102", "histogram requires y_column")
        if y_col not in df.columns:
            raise_http(400, "C103", "Column not found in dataset")

        bins = int(config.get("bins", 20))
        series_data = df[y_col].dropna()
        counts, bin_edges = pd.cut(series_data, bins=bins, retbins=True)
        freq = counts.value_counts(sort=False)

        result["labels"] = [
            f"{round(bin_edges[i], 2)}~{round(bin_edges[i + 1], 2)}"
            for i in range(len(bin_edges) - 1)
        ]
        result["series"] = [{"name": "count", "data": [int(v) for v in freq.values]}]

    return result


def delete_chart(db: Session, dataset_id: int, chart_id: int, user: User) -> None:
    chart = (
        db.query(Chart)
        .filter(Chart.id == chart_id, Chart.dataset_id == dataset_id)
        .first()
    )
    if chart is None:
        raise_http(404, "C101", "Chart not found")
    if chart.user_id != user.id and user.role != "admin":
        raise_http(403, "C102", "Access denied")
    db.delete(chart)
