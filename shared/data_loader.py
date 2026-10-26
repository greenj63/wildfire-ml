"""Loading the shared datasets. This is the ONLY place that knows where data lives."""

from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from shared.utils import get_project_root


def get_dataset_dir(name: str, processed: bool = False) -> Path:
    """Return data/raw/<name>/ (or data/processed/<name>/)."""
    stage = "processed" if processed else "raw"
    return get_project_root() / "data" / stage / name


def load_dataset(
    name: str, filename: str | None = None, processed: bool = False, **read_csv_kwargs
) -> pd.DataFrame:
    """Load a CSV from the shared data folder.

    If `filename` is not given, the folder must contain exactly one CSV.
    Extra keyword arguments go to pd.read_csv (e.g. low_memory=False).
    """
    folder = get_dataset_dir(name, processed)
    if not folder.exists():
        raise FileNotFoundError(
            f"Dataset folder not found: {folder}. "
            "Check data/README.md for how to download it."
        )
    if filename is None:
        csvs = list(folder.glob("*.csv"))
        if len(csvs) != 1:
            raise ValueError(
                f"Expected exactly one CSV in {folder}, found {len(csvs)}. "
                "Pass filename=... to choose one."
            )
        return pd.read_csv(csvs[0], **read_csv_kwargs)
    return pd.read_csv(folder / filename, **read_csv_kwargs)


def split_data(
    df: pd.DataFrame, target_column: str, test_size: float = 0.2, seed: int = 42
):
    """Split a DataFrame into X_train, X_test, y_train, y_test."""
    X = df.drop(columns=[target_column])
    y = df[target_column]
    return train_test_split(X, y, test_size=test_size, random_state=seed)
