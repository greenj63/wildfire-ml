"""WHAT the model is. Only define the model here: no data loading, no training."""

from sklearn.base import BaseEstimator
from sklearn.ensemble import RandomForestRegressor

MEMBER = "Erick Sanchez"

# Added max_features per the team update to handle the 42 new dataset features
PARAM_GRID = {
    "max_depth": [10, 20, None],
    "min_samples_leaf": [2, 5, 10],
    "min_samples_split": [2, 10],
    "n_estimators": [100, 200],
    "max_features": [0.3, 0.5, "sqrt"],
}


def build_model(seed: int, **params) -> BaseEstimator:
    """Create and return an UNTRAINED regressor."""
    # Added criterion="absolute_error" to aim for the MEDIAN (typical fires)
    return RandomForestRegressor(
        random_state=seed, n_jobs=-1, criterion="absolute_error", **params
    )
