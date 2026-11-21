"""Shared schema for ML results (gold.ml_model_metrics)."""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelMetrics(BaseModel):
    """Metrics of 1 model × 1 version, grouped by dataset (test / validation / backtest...)."""

    model_name: str
    model_version: str
    trained_at: datetime
    metrics: dict[str, dict[str, float]] = Field(
        description="{dataset: {metric_name: value}}, e.g. {'test': {'auc': 0.888}}. "
        "Rates are stored as 0–1"
    )


class ModelMetricsResponse(BaseModel):
    models: list[ModelMetrics]
