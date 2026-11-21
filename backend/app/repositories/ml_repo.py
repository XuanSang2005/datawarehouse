"""Read the ML result tables (gold.ml_*). Created by the scripts in ml/, they may NOT exist yet."""

from sqlalchemy import Connection, text


def table_exists(conn: Connection, qualified_name: str) -> bool:
    """Check a table exists without aborting the transaction (to_regclass returns NULL)."""
    return bool(
        conn.execute(
            text("SELECT to_regclass(:name) IS NOT NULL"), {"name": qualified_name}
        ).scalar()
    )


def fetch_model_metrics(conn: Connection, name_prefix: str) -> list[dict]:
    query = text(
        """
        SELECT model_name, model_version, dataset, metric_name, metric_value, trained_at
        FROM gold.ml_model_metrics
        WHERE model_name LIKE :prefix
        ORDER BY model_name, model_version, dataset, metric_name
        """
    )
    return [dict(r) for r in conn.execute(query, {"prefix": f"{name_prefix}%"}).mappings()]


def fetch_metric_value(
    conn: Connection, model_name: str, metric_name: str, dataset: str
) -> float | None:
    """One metric value of the latest version (e.g. the threshold_high of cancellation_gbm)."""
    query = text(
        """
        SELECT metric_value
        FROM gold.ml_model_metrics
        WHERE model_name = :model_name AND metric_name = :metric_name AND dataset = :dataset
        ORDER BY trained_at DESC
        LIMIT 1
        """
    )
    value = conn.execute(
        query, {"model_name": model_name, "metric_name": metric_name, "dataset": dataset}
    ).scalar()
    return float(value) if value is not None else None


def fetch_risk_versions(conn: Connection) -> list[str]:
    """Versions scored in gold.ml_booking_risk, newest first."""
    query = text(
        """
        SELECT model_version
        FROM gold.ml_booking_risk
        GROUP BY model_version
        ORDER BY max(scored_at) DESC
        """
    )
    return list(conn.execute(query).scalars())
