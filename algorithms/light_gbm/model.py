"""WHAT the model is. Only define the model here: no data loading, no training."""

import lightgbm as lgb

MEMBER = "Arlim Macaldo"

# Stage 1 (54 combinations, results in tuning/stage1_metrics.json) tried objective
# l2/l1/huber, num_leaves 15/31/63, learning_rate 0.03/0.05/0.1, and
# min_child_samples 20/50, with LightGBM's default 100 trees. Best: objective l1,
# num_leaves 63, learning_rate 0.1, min_child_samples 50 (validation MAE 0.5706).
#
# Stage 2: objective, min_child_samples, and 500 trees are fixed below. num_leaves and
# learning_rate were at the top of their stage 1 ranges, so the search goes higher,
# and row/feature sampling is added.
PARAM_GRID = {
    "num_leaves": [63, 127],  # tree complexity
    "learning_rate": [0.05, 0.1],  # step size per tree
    "subsample": [0.8, 1.0],  # share of rows each tree sees
    "colsample_bytree": [0.8, 1.0],  # share of features each tree sees
}


def build_model(seed: int, **params) -> lgb.LGBMRegressor:
    """An untrained LightGBM regressor (gradient-boosted decision trees).

    Fixed settings (not tuned in stage 2):
    - objective "l1": trees minimize absolute error, matching the team's MAE metric.
      This was the biggest gain in stage 1.
    - n_estimators 500: stage 1 used the default 100 trees.
    - min_child_samples 50: best in stage 1.
    - subsample_freq 1: without it, LightGBM ignores `subsample`.
    - verbose -1: no LightGBM messages on every fit.
    """
    return lgb.LGBMRegressor(
        objective="l1",
        n_estimators=500,
        min_child_samples=50,
        subsample_freq=1,
        verbose=-1,
        random_state=seed,
        **params,
    )
