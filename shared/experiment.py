"""The shared experiment: target, features, and split. Every model uses these.

See docs/evaluation_plan.md for the reasoning behind each choice.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

from shared.data_loader import get_dataset_dir

DATASET_NAME = "wildfire_drought"
DATASET_FILENAME = "wildfire_drought.csv"

# log(1 + acres burned per day until containment)
TARGET_COLUMN = "LOG_SPREAD_RATE"

# Only things known when a fire is discovered (no leakage)
NUMERIC_FEATURES = [
    "LATITUDE",
    "LONGITUDE",
    "DISCOVERY_DOY",
    "DISCOVERY_HOUR",
    "PRECTOT",
    "PS",
    "QV2M",
    "T2M",
    "T2MDEW",
    "T2MWET",
    "T2M_MAX",
    "T2M_MIN",
    "T2M_RANGE",
    "TS",
    "WS10M",
    "WS10M_MAX",
    "WS10M_MIN",
    "WS10M_RANGE",
    "WS50M",
    "WS50M_MAX",
    "WS50M_MIN",
    "WS50M_RANGE",
    "SCORE",
]
CATEGORICAL_FEATURES = ["STATE"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

# Random split with a fixed seed, about 80% train / 10% validation / 10% test. Fires
# from the same county on the same day share identical weather, so each county-day
# goes entirely into one split (otherwise test weather would leak into training).
SPLIT_SEED = 42
VALIDATION_SIZE = 0.1
TEST_SIZE = 0.1
SPLIT_GROUP_COLUMNS = ["DROUGHT_FIPS", "DISCOVERY_DATE"]
SPLIT_NAMES = ["train", "validation", "test"]
SPLIT_DESCRIPTION = (
    f"random ~80/10/10 split, county-days kept together (GroupShuffleSplit, "
    f"seed {SPLIT_SEED}); files in data/processed/{DATASET_NAME}/"
)


def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add DISCOVERY_HOUR (from DISCOVERY_TIME, e.g. 1530 -> 15) and the target.

    Used for training data and for single inputs in predict(), so both match.
    """
    df = df.copy()
    df["DISCOVERY_HOUR"] = pd.to_numeric(df["DISCOVERY_TIME"], errors="coerce") // 100
    if "SPREAD_RATE" in df.columns:
        df[TARGET_COLUMN] = np.log1p(df["SPREAD_RATE"])
    return df


def make_split(df: pd.DataFrame) -> dict:
    """Split fires into {"train": df, "validation": df, "test": df}.

    Same seed, same data -> same split every time.
    """
    groups = df[SPLIT_GROUP_COLUMNS].astype(str).agg("|".join, axis=1)

    # First take the test set, then the validation set from what's left
    test_splitter = GroupShuffleSplit(
        n_splits=1, test_size=TEST_SIZE, random_state=SPLIT_SEED
    )
    rest_idx, test_idx = next(test_splitter.split(df, groups=groups))
    rest = df.iloc[rest_idx]
    val_splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=VALIDATION_SIZE / (1 - TEST_SIZE),
        random_state=SPLIT_SEED,
    )
    train_idx, val_idx = next(val_splitter.split(rest, groups=groups.iloc[rest_idx]))
    parts = {
        "train": rest.iloc[train_idx],
        "validation": rest.iloc[val_idx],
        "test": df.iloc[test_idx],
    }
    return {name: part.sort_values("FOD_ID") for name, part in parts.items()}


def split_path(name: str) -> Path:
    """data/processed/wildfire_drought/<name>.csv"""
    return get_dataset_dir(DATASET_NAME, processed=True) / f"{name}.csv"


def load_experiment_data() -> dict:
    """Load features and target for each split.

    Returns {"train": (X, y), "validation": (X, y), "test": (X, y)}, read from the
    committed train.csv, validation.csv, and test.csv, so every model uses exactly the
    same rows.
    """
    data = {}
    for name in SPLIT_NAMES:
        path = split_path(name)
        if not path.exists():
            raise FileNotFoundError(
                f"Split file not found: {path}. Run git pull (the files are committed)."
            )
        part = add_derived_columns(pd.read_csv(path, low_memory=False))
        data[name] = (part[FEATURES], part[TARGET_COLUMN])
    return data
