"""WHAT the model is. Only define the model here: no data loading, no training."""

from sklearn.base import BaseEstimator
from sklearn.ensemble import RandomForestRegressor

MEMBER = "Erick Sanchez"

# The settings to try. train.py fits one model per combination on the training
# set and keeps the one with the lowest validation MAE.
PARAM_GRID = {
    "max_depth": [10, 20, None],
    "min_samples_leaf": [2, 5, 10],
    "min_samples_split": [2, 10],
    "n_estimators": [100, 200]
}

def build_model(seed: int, **params) -> BaseEstimator:
    """Create and return an UNTRAINED regressor.

    seed: pass it as random_state if your model uses randomness.
    params: one combination from PARAM_GRID, e.g. {"max_depth": 10}.
    """
    return RandomForestRegressor(random_state=seed, n_jobs=-1, **params)