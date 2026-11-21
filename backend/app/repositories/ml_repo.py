"""Đọc các bảng kết quả ML (gold.ml_*). Bảng do script trong ml/ tạo, có thể CHƯA tồn tại."""

from sqlalchemy import Connection, text


def table_exists(conn: Connection, qualified_name: str) -> bool:
    """Kiểm tra bảng tồn tại mà không làm hỏng transaction (to_regclass trả NULL thay vì lỗi)."""
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
    """1 giá trị metric của phiên bản mới nhất (vd ngưỡng threshold_high của cancellation_gbm)."""
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
    """Các phiên bản đã chấm điểm trong gold.ml_booking_risk, mới nhất trước."""
    query = text(
        """
        SELECT model_version
        FROM gold.ml_booking_risk
        GROUP BY model_version
        ORDER BY max(scored_at) DESC
        """
    )
    return list(conn.execute(query).scalars())
