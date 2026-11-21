"""Train + evaluate + score the booking cancellation prediction model (Epic E3).

Run from the repo root:
    python -m ml.cancellation.train                 # train, evaluate, write gold.ml_* (default)
    python -m ml.cancellation.train --no-write      # train + print metrics only, no DB writes

Steps:
    1. Read gold.fact_booking + dimensions (database/ml/21_cancellation_features.sql), drop
       leakage columns.
    2. Time-based split: train = arrival < 2017-01-01, test = year 2017.
       Within train, the last 6 months (2016-07 → 2016-12) are the validation set used to CHOOSE
       the risk band thresholds and hyperparameters (the test set is never looked at):
       High = precision >= 80%, Medium = max F1 (see ml/cancellation/evaluation.py).
    3. Two models: Logistic Regression (baseline) and HistGradientBoosting (main).
       Each model: fit on train before validation → choose thresholds on validation → refit on
       the full train set → evaluate on the 2017 test set.
    4. One extra control model: Gradient Boosting without the country columns (⚠ suspected to be
       recorded at check-in).
    5. Permutation importance (AUC) of the main model on the test set.
    6. Score ALL bookings with the main model → gold.ml_booking_risk;
       metrics → gold.ml_model_metrics.
    7. Save the models to ml/models/ (not committed).
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, OrdinalEncoder, StandardScaler

from etl.db import connect
from ml.cancellation import store
from ml.cancellation.evaluation import (
    RISK_BANDS,
    RiskThresholds,
    assign_risk_band,
    choose_thresholds,
    classification_metrics,
)
from ml.cancellation.features import (
    CATEGORICAL_FEATURES,
    COUNTRY_FEATURES,
    FEATURES,
    ID_COLUMN,
    NUMERIC_FEATURES,
    TARGET,
    build_features,
    in_test_period,
    in_validation_period,
    load_dataset,
)

log = logging.getLogger("ml.cancellation.train")

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
DEFAULT_MODEL_VERSION = "cancellation_v1"
MODEL_LOGREG = "cancellation_logreg"
MODEL_GBM = "cancellation_gbm"
MODEL_GBM_NO_COUNTRY = "cancellation_gbm_no_country"
ALL_MODEL_NAMES = (MODEL_LOGREG, MODEL_GBM, MODEL_GBM_NO_COUNTRY)
PRIMARY_MODEL = MODEL_GBM

RANDOM_STATE = 42
# Categories seen < MIN_FREQUENCY times in the train set are merged into one "infrequent" group.
MIN_FREQUENCY = 100
# Strongly right-skewed numeric columns: log1p before scaling (Logistic Regression only).
SKEWED_FEATURES = [
    "lead_time",
    "weekend_nights",
    "week_nights",
    "total_nights",
    "previous_cancellations",
    "previous_bookings_not_canceled",
    "adr",
    "adr_per_person",
]
IMPORTANCE_SAMPLE = 15_000
IMPORTANCE_REPEATS = 5


def make_logreg() -> Pipeline:
    """Baseline: one-hot + log/scaling + Logistic Regression."""
    skewed = [c for c in NUMERIC_FEATURES if c in SKEWED_FEATURES]
    plain = [c for c in NUMERIC_FEATURES if c not in SKEWED_FEATURES]
    pre = ColumnTransformer(
        [
            (
                "cat",
                OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=MIN_FREQUENCY),
                CATEGORICAL_FEATURES,
            ),
            (
                "skewed",
                Pipeline(
                    [
                        ("log1p", FunctionTransformer(np.log1p, feature_names_out="one-to-one")),
                        ("scale", StandardScaler()),
                    ]
                ),
                skewed,
            ),
            ("num", StandardScaler(), plain),
        ]
    )
    clf = LogisticRegression(max_iter=3000, C=1.0)
    return Pipeline([("pre", pre), ("clf", clf)])


def make_gbm(features: list[str] | None = None) -> Pipeline:
    """Main model: HistGradientBoosting, categorical columns use native categorical splits."""
    features = features or FEATURES
    cat = [c for c in CATEGORICAL_FEATURES if c in features]
    num = [c for c in NUMERIC_FEATURES if c in features]
    pre = ColumnTransformer(
        [
            (
                "cat",
                OrdinalEncoder(
                    handle_unknown="use_encoded_value",
                    unknown_value=-1,  # negative value = missing for HistGradientBoosting
                    encoded_missing_value=-1,
                    min_frequency=MIN_FREQUENCY,
                    max_categories=250,  # HGB requires categories < max_bins (255)
                ),
                cat,
            ),
            ("num", "passthrough", num),
        ]
    )
    clf = HistGradientBoostingClassifier(
        # Shallow trees + large leaves: chosen by validation AUC (2016-H2). Deep trees (63 leaves)
        # reach train AUC 0.99 but only 0.83 on validation: they memorize duplicated group bookings.
        learning_rate=0.05,
        max_iter=400,
        max_leaf_nodes=7,
        min_samples_leaf=200,
        l2_regularization=1.0,
        categorical_features=list(range(len(cat))),
        early_stopping=False,
        random_state=RANDOM_STATE,
    )
    return Pipeline([("pre", pre), ("clf", clf)])


def _proba(model: Pipeline, X: pd.DataFrame) -> np.ndarray:
    return model.predict_proba(X)[:, 1]


def fit_and_evaluate(name, factory, X, y, is_train, is_val, is_test) -> dict:
    """Choose thresholds on validation, then refit on the full train set and evaluate on test."""
    start = time.perf_counter()
    fit_part = is_train & ~is_val
    model = factory().fit(X[fit_part], y[fit_part])
    val_proba = _proba(model, X[is_val])
    thresholds = choose_thresholds(y[is_val], val_proba)
    val_metrics = classification_metrics(y[is_val], val_proba, thresholds.high)

    model = factory().fit(X[is_train], y[is_train])
    train_metrics = classification_metrics(y[is_train], _proba(model, X[is_train]), thresholds.high)
    test_proba = _proba(model, X[is_test])
    test_metrics = classification_metrics(y[is_test], test_proba, thresholds.high)
    # Also precision/recall/F1 when Medium + High are combined (p >= Medium threshold)
    at_medium = classification_metrics(y[is_test], test_proba, thresholds.medium)
    for key in ("precision", "recall", "f1"):
        test_metrics[f"{key}_at_medium"] = at_medium[key]
    log.info(
        "%s: AUC test=%.4f (train=%.4f, val=%.4f), thresholds Medium=%.2f High=%.2f, %.0fs",
        name,
        test_metrics["auc"],
        train_metrics["auc"],
        val_metrics["auc"],
        thresholds.medium,
        thresholds.high,
        time.perf_counter() - start,
    )
    return {
        "name": name,
        "model": model,
        "thresholds": thresholds,
        "metrics": {"train": train_metrics, "validation": val_metrics, "test": test_metrics},
        "test_proba": test_proba,
    }


def band_summary(y, proba, thresholds: RiskThresholds) -> dict[str, dict[str, float]]:
    """Bookings and actual cancellation rate in each risk band (recomputed from totals)."""
    bands = assign_risk_band(proba, thresholds)
    y = np.asarray(y)
    out = {}
    for band in RISK_BANDS:
        mask = bands == band
        n = int(mask.sum())
        out[band] = {
            "bookings": float(n),
            "share": float(n / len(y)) if len(y) else 0.0,
            "cancel_rate": float(y[mask].sum() / n) if n else 0.0,
        }
    return out


def metric_rows(results: list[dict], bands_test: dict, ablation: dict) -> list[store.MetricRow]:
    rows: list[store.MetricRow] = []
    for res in results:
        for dataset, metrics in res["metrics"].items():
            for metric_name, value in metrics.items():
                if metric_name == "threshold":
                    continue  # written separately as threshold_medium / threshold_high
                rows.append((res["name"], metric_name, value, dataset))
        rows.append((res["name"], "threshold_medium", res["thresholds"].medium, "validation"))
        rows.append((res["name"], "threshold_high", res["thresholds"].high, "validation"))
    for band, stats in bands_test.items():
        for stat, value in stats.items():
            rows.append((PRIMARY_MODEL, f"{band.lower()}_{stat}", value, "test"))
    for metric_name in ("auc", "pr_auc", "brier"):
        rows.append((MODEL_GBM_NO_COUNTRY, metric_name, ablation[metric_name], "test"))
    return rows


def compute_importance(model, X_test, y_test) -> pd.DataFrame:
    rng = np.random.RandomState(RANDOM_STATE)
    idx = rng.choice(len(X_test), size=min(IMPORTANCE_SAMPLE, len(X_test)), replace=False)
    result = permutation_importance(
        model,
        X_test.iloc[idx],
        y_test[idx],
        scoring="roc_auc",
        n_repeats=IMPORTANCE_REPEATS,
        random_state=RANDOM_STATE,
        n_jobs=1,  # avoid CPU/OpenMP contention (HGB is already multi-threaded)
    )
    return (
        pd.DataFrame(
            {
                "feature": X_test.columns,
                "auc_drop_mean": result.importances_mean,
                "auc_drop_std": result.importances_std,
            }
        )
        .sort_values("auc_drop_mean", ascending=False)
        .reset_index(drop=True)
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the booking cancellation model (E3)")
    parser.add_argument("--model-version", default=DEFAULT_MODEL_VERSION)
    parser.add_argument("--no-write", action="store_true", help="Do not write gold.ml_*")
    parser.add_argument(
        "--skip-importance", action="store_true", help="Skip permutation importance"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args(argv)
    trained_at = datetime.now(UTC)

    with connect() as conn:
        raw = load_dataset(conn)
    log.info("Loaded %s bookings from gold.fact_booking", len(raw))

    X = build_features(raw)
    y = raw[TARGET].astype(int).to_numpy()
    is_test = in_test_period(raw).to_numpy()
    is_val = in_validation_period(raw).to_numpy()
    is_train = ~is_test
    log.info(
        "Train %s (of which validation %s), test %s bookings",
        is_train.sum(),
        is_val.sum(),
        is_test.sum(),
    )

    results = [
        fit_and_evaluate(MODEL_LOGREG, make_logreg, X, y, is_train, is_val, is_test),
        fit_and_evaluate(MODEL_GBM, make_gbm, X, y, is_train, is_val, is_test),
    ]
    primary = next(r for r in results if r["name"] == PRIMARY_MODEL)

    # Control model: drop the country columns
    no_country = [c for c in FEATURES if c not in COUNTRY_FEATURES]
    ablation_model = make_gbm(no_country).fit(X.loc[is_train, no_country], y[is_train])
    ablation = classification_metrics(
        y[is_test],
        _proba(ablation_model, X.loc[is_test, no_country]),
        primary["thresholds"].high,
    )
    log.info("%s: AUC test=%.4f", MODEL_GBM_NO_COUNTRY, ablation["auc"])

    # Round to 4 decimals as when writing cancel_probability, so bands match gold.ml_booking_risk
    bands_test = band_summary(y[is_test], primary["test_proba"].round(4), primary["thresholds"])

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    importance = None
    if not args.skip_importance:
        importance = compute_importance(primary["model"], X[is_test], y[is_test])
        importance.to_csv(MODELS_DIR / "cancellation_feature_importance.csv", index=False)
        log.info("Top 10 features (permutation importance, AUC drop):\n%s", importance.head(10))

    # Score all bookings with the main model
    all_proba = np.clip(_proba(primary["model"], X), 0.0, 1.0).round(4)
    scores = pd.DataFrame(
        {
            ID_COLUMN: raw[ID_COLUMN].to_numpy(),
            "cancel_probability": all_proba,
            "risk_band": assign_risk_band(all_proba, primary["thresholds"]),
            "is_test_set": is_test,
        }
    )

    for res in results:
        joblib.dump(
            {
                "model": res["model"],
                "model_version": args.model_version,
                "model_name": res["name"],
                "features": FEATURES,
                "thresholds": {
                    "medium": res["thresholds"].medium,
                    "high": res["thresholds"].high,
                },
                "trained_at": trained_at.isoformat(),
            },
            MODELS_DIR / f"{res['name']}.joblib",
        )
    report = {
        "model_version": args.model_version,
        "trained_at": trained_at.isoformat(),
        "models": {
            r["name"]: {
                "thresholds": {"medium": r["thresholds"].medium, "high": r["thresholds"].high},
                "metrics": r["metrics"],
            }
            for r in results
        },
        MODEL_GBM_NO_COUNTRY: ablation,
        "risk_bands_test": bands_test,
        "risk_bands_all": scores["risk_band"].value_counts().to_dict(),
        "feature_importance_top15": (
            importance.head(15).to_dict(orient="records") if importance is not None else None
        ),
    }
    (MODELS_DIR / "cancellation_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in report.items() if k != "models"}, indent=2))
    for r in results:
        print(r["name"], json.dumps(r["metrics"]["test"], indent=2))

    if args.no_write:
        log.info("--no-write: skipping DB writes")
        return

    rows = metric_rows(results, bands_test, ablation)
    with connect() as conn:  # 1 transaction: commit when leaving the with block, rollback on error
        store.ensure_tables(conn)
        n_risk = store.write_booking_risk(conn, scores, args.model_version, trained_at)
        n_metrics = store.write_metrics(conn, rows, ALL_MODEL_NAMES, args.model_version, trained_at)
    log.info(
        "Wrote %s rows to gold.ml_booking_risk, %s to gold.ml_model_metrics (model_version=%s)",
        n_risk,
        n_metrics,
        args.model_version,
    )


if __name__ == "__main__":
    main()
