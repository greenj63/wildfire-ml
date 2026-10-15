"""Small helpers used everywhere: paths, random seed, saving/loading models."""

import json
import random
from pathlib import Path

import joblib
import numpy as np


def get_project_root() -> Path:
    """Return the repo root folder, no matter where you run Python from."""
    return Path(__file__).resolve().parent.parent


def set_random_seed(seed: int = 42) -> None:
    """Make results repeatable."""
    random.seed(seed)
    np.random.seed(seed)


def get_model_dir(algorithm_name: str) -> Path:
    """Return (and create) models/<algorithm_name>/."""
    path = get_project_root() / "models" / algorithm_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_model(model, algorithm_name: str, filename: str = "model.joblib") -> Path:
    """Save a trained model to models/<algorithm_name>/<filename>."""
    path = get_model_dir(algorithm_name) / filename
    joblib.dump(model, path)
    return path


def load_model(algorithm_name: str, filename: str = "model.joblib"):
    """Load a saved model from models/<algorithm_name>/<filename>."""
    path = get_model_dir(algorithm_name) / filename
    if not path.exists():
        raise FileNotFoundError(
            f"No saved model at {path}. Run the training script first: "
            f"python -m algorithms.{algorithm_name}.train"
        )
    return joblib.load(path)


def save_metrics(metrics: dict, algorithm_name: str) -> Path:
    """Save results to models/<algorithm_name>/metrics.json."""
    path = get_model_dir(algorithm_name) / "metrics.json"
    path.write_text(json.dumps(metrics, indent=2))
    return path
