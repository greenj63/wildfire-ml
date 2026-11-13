"""Run every trained algorithm on one sample row."""

import importlib

from shared.utils import get_project_root

PRIMARY_MODEL = "light_gbm"  # best model in results/comparison.csv
LABELS = {
    "light_gbm": "LightGBM",
    "random_forest": "Random Forest",
    "knn": "k-Nearest Neighbors",
    "huber-regression": "Huber Regression",
    "baseline": "Baseline",
}


def algorithm_names() -> list[str]:
    """Folders in algorithms/ that have a predict.py (the template is skipped)."""
    folder = get_project_root() / "algorithms"
    names = [
        path.name
        for path in folder.iterdir()
        if path.is_dir()
        and not path.name.startswith("_")
        and (path / "predict.py").exists()
    ]
    # The headline model first, the rest alphabetically
    return sorted(names, key=lambda name: (name != PRIMARY_MODEL, name))


def is_trained(name: str) -> bool:
    return (get_project_root() / "models" / name / "model.joblib").exists()


def predict_all(record: dict) -> list[dict]:
    """Spread rate (acres/day) from each algorithm; untrained ones say so."""
    results = []
    for name in algorithm_names():
        entry = {"name": name, "label": LABELS.get(name, name), "spread_rate": None}
        if not is_trained(name):
            entry["status"] = "not_trained"
        else:
            try:
                predict = importlib.import_module(f"algorithms.{name}.predict").predict
                entry["spread_rate"] = round(predict(record), 2)
                entry["status"] = "ok"
            except Exception:  # one broken model should not hide the others
                entry["status"] = "error"
        results.append(entry)
    return results
