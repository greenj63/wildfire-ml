"""WHAT the model is. Only define the model here: no data loading, no training."""

from sklearn.base import BaseEstimator
from sklearn.linear_model import HuberRegressor

# Member Name (shown in results/comparison.csv)
MEMBER = "Jack Greene"

# The settings to try for this model
PARAM_GRID = {
    "epsilon": [1.0, 1.1, 1.15, 1.25, 1.35],
    "alpha": [1e-6, 1e-4, 1e-2, 1],
}


def build_model(seed: int, **params) -> BaseEstimator:
    """Create and return an UNTRAINED regressor.

    seed: pass it as random_state if your model uses randomness.
    params: one combination from PARAM_GRID, e.g. {"max_depth": 10}.

    The shared preprocessing (fill gaps, scale, one-hot STATE) runs before this
    model, so it gets clean numeric input. To add model-specific steps, return a
    Pipeline and explain why in your README.
    """

    return HuberRegressor(max_iter=500, **params)
