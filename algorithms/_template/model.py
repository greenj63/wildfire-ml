"""WHAT the model is. Only define the model here: no data loading, no training."""

from sklearn.base import BaseEstimator

# TODO: your name (shown in results/comparison.csv)
MEMBER = "your name"

# TODO: the settings to try. train.py fits one model per combination on the training
# set and keeps the one with the lowest validation MAE. Leave {} to use defaults.
# Example: {"max_depth": [5, 10, None], "n_estimators": [100, 300]}
PARAM_GRID = {}


def build_model(seed: int, **params) -> BaseEstimator:
    """Create and return an UNTRAINED regressor.

    seed: pass it as random_state if your model uses randomness.
    params: one combination from PARAM_GRID, e.g. {"max_depth": 10}.

    The shared preprocessing (fill gaps, scale, one-hot STATE) runs before this
    model, so it gets clean numeric input. To add model-specific steps, return a
    Pipeline and explain why in your README.

    TODO: replace the error below with your model, for example:
        from sklearn.linear_model import Ridge
        return Ridge(**params)
    """
    raise NotImplementedError("TODO: build and return your model in model.py")
