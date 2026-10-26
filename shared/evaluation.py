"""Metrics, so that "accuracy" means the same thing for every algorithm."""

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)


def accuracy(y_true, y_pred) -> float:
    return float(accuracy_score(y_true, y_pred))


def rmse(y_true, y_pred) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def r2(y_true, y_pred) -> float:
    return float(r2_score(y_true, y_pred))


def mae(y_true, y_pred) -> float:
    return float(mean_absolute_error(y_true, y_pred))


def evaluate_classification(y_true, y_pred) -> dict:
    """Metrics dict for classification; save it with save_metrics()."""
    return {
        "accuracy": accuracy(y_true, y_pred),
        "f1_weighted": float(f1_score(y_true, y_pred, average="weighted")),
    }


def evaluate_regression(y_true, y_pred) -> dict:
    """Metrics dict for regression; save it with save_metrics()."""
    return {"rmse": rmse(y_true, y_pred), "r2": r2(y_true, y_pred)}


def evaluate_spread_rate(y_true, y_pred) -> dict:
    """Metrics for the shared experiment (target = log(1 + spread rate)).

    mae is the primary metric. mae_top10 is the MAE on the 10% fastest-spreading
    fires in y_true; it catches models that only ever predict "small fire".
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    top10 = y_true >= np.quantile(y_true, 0.9)
    return {
        "mae": mae(y_true, y_pred),
        "rmse": rmse(y_true, y_pred),
        "r2": r2(y_true, y_pred),
        "mae_top10": mae(y_true[top10], y_pred[top10]),
    }
