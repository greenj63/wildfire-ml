import numpy as np
import pandas as pd

from shared.evaluation import evaluate_spread_rate
from shared.experiment import (
    CATEGORICAL_FEATURES,
    FEATURES,
    NUMERIC_FEATURES,
    TARGET_COLUMN,
    add_derived_columns,
    category_code,
    make_split,
    percentile_midpoint,
)
from shared.preprocessing import build_preprocessor

DERIVED = {
    "DISCOVERY_HOUR",
    "ASPECT_SIN",
    "ASPECT_COS",
    "ASPECT_FLAT",
    "WIND_DIR_SIN",
    "WIND_DIR_COS",
    "FIRE_STATIONS_10KM",
    "FIRE_STATIONS_20KM",
}


def fake_fires(years) -> pd.DataFrame:
    """Small made-up dataset with the experiment's raw columns (no real data needed)."""
    rng = np.random.default_rng(0)
    n = len(years)
    raw_numeric = [
        c for c in NUMERIC_FEATURES if c not in DERIVED and not c.endswith("PERCENTILE")
    ]
    df = pd.DataFrame(rng.normal(size=(n, len(raw_numeric))), columns=raw_numeric)
    df["STATE"] = rng.choice(["CA", "NV", "AZ"], size=n)
    df["Land_Cover"] = rng.choice([42.0, 52.0, 71.0], size=n)
    df["OWNER_DESCR"] = rng.choice(["USFS", "BLM", "PRIVATE"], size=n)
    df["NWCG_REPORTING_AGENCY"] = rng.choice(["FS", "BLM"], size=n)
    df["Ecoregion_NA_L2CODE"] = rng.choice([6.2, 10.1], size=n)
    df["Aspect"] = rng.integers(-1, 360, size=n)
    df["th"] = rng.integers(0, 360, size=n)
    for name in ["sph", "vs", "fm100", "bi", "vpd", "erc"]:
        df[f"{name}_Percentile"] = rng.choice(["<10%", "30-50%", ">90%"], size=n)
    df["No_FireStation_10.0km"] = rng.choice([np.nan, 1.0, 3.0], size=n)
    df["No_FireStation_20.0km"] = rng.choice([np.nan, 2.0, 5.0], size=n)
    df["FOD_ID"] = np.arange(n)
    df["FIRE_YEAR"] = years
    df["DISCOVERY_TIME"] = 1530
    df["SPREAD_RATE"] = rng.exponential(size=n)
    return df


def test_split_keeps_county_days_together():
    df = fake_fires([2010] * 300)
    df["DROUGHT_FIPS"] = np.arange(300) % 20
    df["DISCOVERY_DATE"] = "2010-06-01"
    parts = make_split(df)

    ids = [set(part["FOD_ID"]) for part in parts.values()]
    assert sum(len(i) for i in ids) == 300  # every fire is in exactly one split
    assert not (ids[0] & ids[1]) and not (ids[0] & ids[2]) and not (ids[1] & ids[2])
    counties = [set(part["DROUGHT_FIPS"]) for part in parts.values()]
    assert not (counties[0] & counties[1]) and not (counties[0] & counties[2])


def test_split_is_the_same_every_time():
    df = fake_fires([2010] * 300)
    df["DROUGHT_FIPS"] = np.arange(300) % 50
    df["DISCOVERY_DATE"] = "2010-06-01"
    first, second = make_split(df), make_split(df)
    for name in first:
        assert first[name].equals(second[name])


def test_derived_columns():
    df = add_derived_columns(fake_fires([2000]))
    assert df["DISCOVERY_HOUR"].iloc[0] == 15
    assert np.isclose(df[TARGET_COLUMN].iloc[0], np.log1p(df["SPREAD_RATE"].iloc[0]))
    assert set(FEATURES) <= set(df.columns)


def test_directions_and_flat_ground():
    df = fake_fires([2000] * 3)
    df["Aspect"] = [-1, 90, 180]
    df["th"] = [0, 90, 270]
    out = add_derived_columns(df)
    assert list(out["ASPECT_FLAT"]) == [1.0, 0.0, 0.0]
    assert np.allclose(out["ASPECT_SIN"], [0, 1, 0], atol=1e-9)
    assert np.allclose(out["ASPECT_COS"], [0, 0, -1], atol=1e-9)
    assert np.allclose(out["WIND_DIR_SIN"], [0, 1, -1], atol=1e-9)


def test_percentile_ranges_and_codes():
    assert percentile_midpoint("<10%") == 5
    assert percentile_midpoint("30-50%") == 40
    assert percentile_midpoint(">90%") == 95
    assert np.isnan(percentile_midpoint(None))
    # predict() may get 42 where the files have 42.0; both must be the same category
    assert category_code(42.0) == category_code(42) == category_code("42") == "42"
    assert category_code(6.2) == "6.2"
    assert category_code("USFS") == "USFS"
    assert category_code(np.nan) == "missing"


def test_missing_fire_station_counts_mean_none():
    df = fake_fires([2000] * 2)
    df["No_FireStation_10.0km"] = [np.nan, 4.0]
    assert list(add_derived_columns(df)["FIRE_STATIONS_10KM"]) == [0.0, 4.0]


def test_leakage_columns_are_not_features():
    after_the_fire = {"FIRE_SIZE", "FIRE_SIZE_CLASS", "CONT_DATE", "CONT_DOY"}
    after_the_fire |= {"CONT_TIME", "DURATION_DAYS", "SPREAD_RATE", TARGET_COLUMN}
    assert not after_the_fire & set(FEATURES)
    # FPA FOD-Attributes columns that leak: only exist for big fires, or include days
    # after discovery
    assert not [c for c in FEATURES if c.startswith(("MTBS", "ICS_209"))]
    assert not [c for c in FEATURES if "_5D_" in c]
    assert set(FEATURES) == set(NUMERIC_FEATURES) | set(CATEGORICAL_FEATURES)


def test_preprocessing_only_learns_from_training_data():
    df = add_derived_columns(fake_fires([2000] * 50 + [2020] * 50))
    df.loc[:9, "tmmx"] = np.nan
    df.loc[50:, "tmmx"] = 1000.0  # extreme "test" values
    train, test = df.iloc[:50], df.iloc[50:]

    preprocessor = build_preprocessor().fit(train[FEATURES])
    numeric = preprocessor.named_transformers_["numeric"]
    tmmx = NUMERIC_FEATURES.index("tmmx")
    assert numeric["impute"].statistics_[tmmx] == train["tmmx"].median()
    assert numeric["scale"].mean_[tmmx] < 1000  # the test values weren't used
    assert preprocessor.transform(test[FEATURES]).shape[0] == 50


def test_evaluate_spread_rate():
    y_true = np.arange(10, dtype=float)
    scores = evaluate_spread_rate(y_true, y_true + 1)
    assert scores["mae"] == 1.0
    assert scores["rmse"] == 1.0
    assert scores["mae_top10"] == 1.0
    assert set(scores) == {"mae", "rmse", "r2", "mae_top10"}
