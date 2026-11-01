"""KNN regression for the shared wildfire spread-rate experiment.

The common pipeline in algorithms/knn/train.py handles imputing, scaling, and
one-hot encoding of STATE. This module only configures the estimator.
"""

from sklearn.neighbors import KNeighborsRegressor

MEMBER = "Vincent Chen"

PARAM_GRID = {
    "n_neighbors": [5, 15, 31],
    "weights": ["uniform", "distance"],
}


def build_model(seed: int, **params) -> KNeighborsRegressor:
    """Return an unfitted KNN regressor, compatible with the team template.

    KNN itself is deterministic on fixed data, so seed is unused.
    """
    return KNeighborsRegressor(
        algorithm="auto",
        n_jobs=-1,
        **params,
    )
