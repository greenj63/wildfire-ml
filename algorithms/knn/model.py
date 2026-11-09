"""Median-based KNN for the team's wildfire spread-rate regression.

Both variants predict a median of nearby training targets (LOG_SPREAD_RATE):
- weights='uniform': ordinary median of neighboring target values.
- weights='distance': distance-weighted median of neighboring targets.

Shared feature processing and train/validation/test handling stay in train.py.
"""

import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.neighbors import NearestNeighbors
from sklearn.utils.validation import check_consistent_length, check_is_fitted

MEMBER = "Vincent Chen"

PARAM_GRID = {
    "n_neighbors": [5, 15, 31],
    "weights": ["uniform", "distance"],
}


class MedianKNNRegressor(RegressorMixin, BaseEstimator):
    """KNN regression using either ordinary or distance-weighted medians."""

    def __init__(self, n_neighbors=5, weights="uniform", algorithm="auto", n_jobs=-1):
        self.n_neighbors = n_neighbors
        self.weights = weights
        self.algorithm = algorithm
        self.n_jobs = n_jobs

    def fit(self, X, y):
        y = np.asarray(y, dtype=float).reshape(-1)
        check_consistent_length(X, y)
        if self.weights not in {"uniform", "distance"}:
            raise ValueError("weights must be 'uniform' or 'distance'")
        if not 1 <= self.n_neighbors <= len(y):
            raise ValueError("n_neighbors must be between 1 and the training row count")

        self.neighbors_ = NearestNeighbors(
            n_neighbors=self.n_neighbors,
            algorithm=self.algorithm,
            n_jobs=self.n_jobs,
        ).fit(X)
        self.targets_ = y
        self.n_features_in_ = self.neighbors_.n_features_in_
        return self

    def predict(self, X):
        check_is_fitted(self, ["neighbors_", "targets_"])
        distances, indices = self.neighbors_.kneighbors(X, return_distance=True)
        neighbor_y = self.targets_[indices]

        if self.weights == "uniform":
            return np.median(neighbor_y, axis=1)

        # Sort targets and their matching distances together for a weighted median.
        order = np.argsort(neighbor_y, axis=1, kind="stable")
        values = np.take_along_axis(neighbor_y, order, axis=1)
        distances = np.take_along_axis(distances, order, axis=1)

        # If any neighbor has exactly zero distance, use only zero-distance rows.
        zero = distances == 0
        has_zero = zero.any(axis=1, keepdims=True)
        nonzero_weights = 1.0 / np.maximum(distances, 1e-12)
        weights = np.where(has_zero, zero.astype(float), nonzero_weights)

        cumulative = np.cumsum(weights, axis=1)
        halfway = weights.sum(axis=1, keepdims=True) / 2.0
        median_index = np.argmax(cumulative >= halfway, axis=1)
        return values[np.arange(len(values)), median_index]


def build_model(seed: int, **params) -> MedianKNNRegressor:
    """Return an unfitted median-based KNN regressor for the team pipeline."""
    return MedianKNNRegressor(algorithm="auto", n_jobs=-1, **params)
