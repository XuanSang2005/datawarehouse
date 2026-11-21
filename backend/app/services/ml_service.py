"""Shared logic for ML results: check that tables have data, group metrics by model."""

from sqlalchemy import Connection

from app.core.errors import DataNotReadyError
from app.repositories import ml_repo
from app.schemas.ml import ModelMetrics

TRAIN_COMMANDS = {
    "gold.ml_booking_risk": "OMP_NUM_THREADS=2 python -m ml.cancellation.train",
    "gold.ml_demand_forecast": "python -m ml.forecast.train",
    "gold.ml_model_metrics": "python -m ml.cancellation.train && python -m ml.forecast.train",
}


def require_table(conn: Connection, qualified_name: str) -> None:
    if not ml_repo.table_exists(conn, qualified_name):
        raise not_ready(qualified_name)


def not_ready(qualified_name: str) -> DataNotReadyError:
    return DataNotReadyError(
        f"No ML results in {qualified_name} yet",
        hint=f"Run from the repo root: {TRAIN_COMMANDS.get(qualified_name, 'the scripts in ml/')}",
    )


def group_metrics(rows: list[dict]) -> list[ModelMetrics]:
    """Group rows (model × version × dataset × metric) into 1 object per model × version."""
    grouped: dict[tuple[str, str], ModelMetrics] = {}
    for r in rows:
        key = (r["model_name"], r["model_version"])
        item = grouped.get(key)
        if item is None:
            item = ModelMetrics(
                model_name=r["model_name"],
                model_version=r["model_version"],
                trained_at=r["trained_at"],
                metrics={},
            )
            grouped[key] = item
        item.trained_at = max(item.trained_at, r["trained_at"])
        item.metrics.setdefault(r["dataset"], {})[r["metric_name"]] = float(r["metric_value"])
    return list(grouped.values())


def get_model_metrics(conn: Connection, name_prefix: str, source_table: str) -> list[ModelMetrics]:
    """Metrics of the models whose name starts with `name_prefix`. Clear 404 if not trained yet."""
    require_table(conn, "gold.ml_model_metrics")
    models = group_metrics(ml_repo.fetch_model_metrics(conn, name_prefix))
    if not models:
        raise not_ready(source_table)
    return models
