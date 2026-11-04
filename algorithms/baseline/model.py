"""WHAT the model is. Only define the model here: no data loading, no training."""

from sklearn.dummy import DummyRegressor

MEMBER = "Arlim Macaldo"

# Nothing to tune: the baseline always predicts the same number.
PARAM_GRID = {}


def build_model(seed: int, **params) -> DummyRegressor:
    """The baseline: always predicts the median of the training target.

    It ignores every feature. The median is the best single constant under MAE (the
    team's primary metric), so every real model has to beat this to show it learned
    something from location, weather, terrain, and the rest.

    seed is unused: the baseline has no randomness.
    """
    return DummyRegressor(strategy="median")
