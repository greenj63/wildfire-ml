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

# Only things known when a fire is discovered (no leakage). Besides location and
# timing, they come from FPA FOD-Attributes (Pourmohamad et al., 2024): terrain,
# vegetation, gridMET weather at the ignition point, and who responds. The county
# weather columns (PRECTOT, T2M, WS10M, ...) are still in the files but not used: on
# validation they added nothing once the point weather was in (docs/discussion_log.md).
NUMERIC_FEATURES = [
    # Location and timing
    "LATITUDE",
    "LONGITUDE",
    "DISCOVERY_DOY",
    "DISCOVERY_HOUR",
    # Drought (weekly county score)
    "SCORE",
    # Terrain
    "Elevation",
    "Slope",
    "TPI",
    "TRI",
    "ASPECT_SIN",
    "ASPECT_COS",
    "ASPECT_FLAT",
    # Vegetation
    "NDVI-1day",
    # Weather and fire danger at the ignition point on the discovery day (gridMET)
    "pr",
    "tmmn",
    "tmmx",
    "rmin",
    "rmax",
    "sph",
    "vs",
    "srad",
    "vpd",
    "erc",
    "bi",
    "fm100",
    "fm1000",
    "WIND_DIR_SIN",
    "WIND_DIR_COS",
    # How unusual the day was for that place (midpoint of the percentile range)
    "sph_PERCENTILE",
    "vs_PERCENTILE",
    "fm100_PERCENTILE",
    "bi_PERCENTILE",
    "vpd_PERCENTILE",
    "erc_PERCENTILE",
    # Response and people
    "FIRE_STATIONS_10KM",
    "FIRE_STATIONS_20KM",
    "Population",
]
CATEGORICAL_FEATURES = [
    "STATE",
    "Land_Cover",
    "OWNER_DESCR",
    "NWCG_REPORTING_AGENCY",
    "Ecoregion_NA_L2CODE",
]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

PERCENTILE_COLUMNS = [
    "sph_Percentile",
    "vs_Percentile",
    "fm100_Percentile",
    "bi_Percentile",
    "vpd_Percentile",
    "erc_Percentile",
]

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


def percentile_midpoint(value) -> float:
    """Percentile ranges stored as text -> a number: "30-50%" -> 40, "<10%" -> 5,
    ">90%" -> 95. Empty stays empty."""
    if pd.isna(value):
        return np.nan
    text = str(value).strip().rstrip("%")
    if text.startswith("<"):
        return float(text[1:]) / 2
    if text.startswith(">"):
        return (float(text[1:]) + 100) / 2
    low, high = text.split("-")
    return (float(low) + float(high)) / 2


def category_code(value) -> str:
    """Category codes as text, so 42, 42.0 and "42" all become "42"."""
    if pd.isna(value):
        return "missing"
    number = pd.to_numeric(value, errors="coerce")
    return str(value) if pd.isna(number) else f"{number:g}"


def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Turn raw columns into model features, and add the target if SPREAD_RATE exists.

    Used for training data and for single inputs in predict(), so both match.
    """
    df = df.copy()
    df["DISCOVERY_HOUR"] = pd.to_numeric(df["DISCOVERY_TIME"], errors="coerce") // 100

    # Directions are angles (359 degrees is next to 1), so use sine and cosine.
    # Aspect -1 means flat ground, which has no direction.
    aspect = pd.to_numeric(df["Aspect"], errors="coerce")
    flat = aspect < 0
    df["ASPECT_FLAT"] = flat.astype(float)
    df["ASPECT_SIN"] = np.where(flat, 0.0, np.sin(np.radians(aspect)))
    df["ASPECT_COS"] = np.where(flat, 0.0, np.cos(np.radians(aspect)))
    wind_direction = np.radians(pd.to_numeric(df["th"], errors="coerce"))
    df["WIND_DIR_SIN"] = np.sin(wind_direction)
    df["WIND_DIR_COS"] = np.cos(wind_direction)

    for column in PERCENTILE_COLUMNS:
        name = column.replace("_Percentile", "_PERCENTILE")
        df[name] = df[column].map(percentile_midpoint)

    # The source never records 0 stations, so an empty count means none nearby
    df["FIRE_STATIONS_10KM"] = df["No_FireStation_10.0km"].fillna(0)
    df["FIRE_STATIONS_20KM"] = df["No_FireStation_20.0km"].fillna(0)

    for column in CATEGORICAL_FEATURES:
        df[column] = df[column].map(category_code)

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
    """data/processed/wildfire_drought/<name>.csv.gz (compressed to stay small in Git;
    pandas reads it like a normal CSV)."""
    return get_dataset_dir(DATASET_NAME, processed=True) / f"{name}.csv.gz"


def load_experiment_data() -> dict:
    """Load features and target for each split.

    Returns {"train": (X, y), "validation": (X, y), "test": (X, y)}, read from the
    committed train.csv.gz, validation.csv.gz, and test.csv.gz, so every model uses
    exactly the same rows.
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
