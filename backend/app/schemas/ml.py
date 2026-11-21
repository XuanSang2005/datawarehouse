"""Schema dùng chung cho kết quả ML (gold.ml_model_metrics)."""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelMetrics(BaseModel):
    """Metric của 1 model × 1 phiên bản, nhóm theo tập dữ liệu (test / validation / backtest...)."""

    model_name: str
    model_version: str
    trained_at: datetime
    metrics: dict[str, dict[str, float]] = Field(
        description="{dataset: {metric_name: value}}, vd {'test': {'auc': 0.888}}. "
        "Tỉ lệ lưu dạng 0–1"
    )


class ModelMetricsResponse(BaseModel):
    models: list[ModelMetrics]
