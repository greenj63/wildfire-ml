"""HOW the model learns. Run from the repo root:

python -m algorithms.<your_folder_name>.train

Follows the shared protocol in docs/evaluation_plan.md, so you shouldn't need to
change this file. Your model choices go in model.py.
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import ParameterGrid
from sklearn.pipeline import Pipeline

from shared.evaluation import evaluate_spread_rate
from shared.experiment import SPLIT_DESCRIPTION, TARGET_COLUMN, load_experiment_data
from shared.preprocessing import build_preprocessor
from shared.utils import get_versions, save_metrics, save_model, set_random_seed

from .model import MEMBER, PARAM_GRID, build_model

# The folder name is used automatically, so you never have to rename it here.
ALGORITHM_NAME = Path(__file__).resolve().parent.name

# One run per seed. If your model has no randomness, set SEEDS = [0] and say so in
# your README.
SEEDS = [0, 1, 2, 3, 4]


def make_pipeline(seed: int, params: dict) -> Pipeline:
    """Shared preprocessing + your model. Fitted on training data only."""
    return Pipeline(
        [("preprocess", build_preprocessor()), ("model", build_model(seed, **params))]
    )


def fit_and_score(seed, params, X_fit, y_fit, X_eval, y_eval):
    pipeline = make_pipeline(seed, params)
    start = time.perf_counter()
    pipeline.fit(X_fit, y_fit)
    fit_seconds = time.perf_counter() - start
    return pipeline, evaluate_spread_rate(y_eval, pipeline.predict(X_eval)), fit_seconds


def summarize(runs: list[dict], part: str) -> dict:
    """Mean and standard deviation of each metric across seeds."""
    table = pd.DataFrame([run[part] for run in runs])
    return {
        metric: {"mean": float(table[metric].mean()), "std": float(table[metric].std())}
        for metric in table.columns
    }


def main() -> None:
    data = load_experiment_data()
    X_train, y_train = data["train"]
    X_val, y_val = data["validation"]
    X_test, y_test = data["test"]

    # 1. Tune: try each setting on train, score on validation (never on test)
    search = []
    for params in ParameterGrid(PARAM_GRID):
        set_random_seed(SEEDS[0])
        _, scores, _ = fit_and_score(SEEDS[0], params, X_train, y_train, X_val, y_val)
        search.append({"params": params, "validation_mae": scores["mae"]})
        print(f"{params} -> validation MAE {scores['mae']:.4f}")

    # 2. Freeze the best setting before looking at the test set
    best_params = min(search, key=lambda s: s["validation_mae"])["params"]
    print(f"Best setting: {best_params}")

    # 3. For each seed: validation score (fit on train), then test score (refit on
    #    train + validation)
    X_train_val = pd.concat([X_train, X_val])
    y_train_val = pd.concat([y_train, y_val])
    runs = []
    final_model = None
    for seed in SEEDS:
        set_random_seed(seed)
        _, val_scores, _ = fit_and_score(
            seed, best_params, X_train, y_train, X_val, y_val
        )
        model, test_scores, fit_seconds = fit_and_score(
            seed, best_params, X_train_val, y_train_val, X_test, y_test
        )
        runs.append(
            {
                "seed": seed,
                "validation": val_scores,
                "test": test_scores,
                "fit_seconds": fit_seconds,
            }
        )
        if final_model is None:
            final_model = model
        print(f"seed {seed}: validation {val_scores} | test {test_scores}")

    metrics = {
        "algorithm": ALGORITHM_NAME,
        "member": MEMBER,
        "target": TARGET_COLUMN,
        "split": SPLIT_DESCRIPTION,
        "split_sizes": {name: len(y) for name, (_, y) in data.items()},
        "param_grid": PARAM_GRID,
        "search": search,
        "best_params": best_params,
        "seeds": SEEDS,
        "runs": runs,
        "validation": summarize(runs, "validation"),
        "test": summarize(runs, "test"),
        "fit_seconds_mean": float(np.mean([run["fit_seconds"] for run in runs])),
        "versions": get_versions(),
    }

    # 4. Save the first seed's final model and all results to models/<algorithm_name>/
    save_model(final_model, ALGORITHM_NAME)
    save_metrics(metrics, ALGORITHM_NAME)
    print(f"Test MAE: {metrics['test']['mae']['mean']:.4f}")


if __name__ == "__main__":
    main()
