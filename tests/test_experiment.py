import numpy as np
import pandas as pd

from shared.evaluation import evaluate_spread_rate
from shared.experiment import (
    CATEGORICAL_FEATURES,
    FEATURES,
    NUMERIC_FEATURES,
    TARGET_COLUMN,
    add_derived_columns,
    make_split,
)
from shared.preprocessing import build_preprocessor


def fake_fires(years) -> pd.DataFrame:
    """Small made-up dataset with the experiment's columns (no real data needed)."""
    rng = np.random.default_rng(0)
    n = len(years)
    df = pd.DataFrame(
        rng.normal(size=(n, len(NUMERIC_FEATURES))), columns=NUMERIC_FEATURES
    )
    df["STATE"] = rng.choice(["CA", "NV", "AZ"], size=n)
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


def test_leakage_columns_are_not_features():
    after_the_fire = {"FIRE_SIZE", "FIRE_SIZE_CLASS", "CONT_DATE", "CONT_DOY"}
    after_the_fire |= {"CONT_TIME", "DURATION_DAYS", "SPREAD_RATE", TARGET_COLUMN}
    assert not after_the_fire & set(FEATURES)
    assert set(FEATURES) == set(NUMERIC_FEATURES) | set(CATEGORICAL_FEATURES)


def test_preprocessing_only_learns_from_training_data():
    df = add_derived_columns(fake_fires([2000] * 50 + [2020] * 50))
    df.loc[:9, "T2M"] = np.nan
    df.loc[50:, "T2M"] = 1000.0  # extreme "test" values
    train, test = df.iloc[:50], df.iloc[50:]

    preprocessor = build_preprocessor().fit(train[FEATURES])
    numeric = preprocessor.named_transformers_["numeric"]
    t2m = NUMERIC_FEATURES.index("T2M")
    assert numeric["impute"].statistics_[t2m] == train["T2M"].median()
    assert numeric["scale"].mean_[t2m] < 1000  # the test values weren't used
    assert preprocessor.transform(test[FEATURES]).shape[0] == 50


def test_evaluate_spread_rate():
    y_true = np.arange(10, dtype=float)
    scores = evaluate_spread_rate(y_true, y_true + 1)
    assert scores["mae"] == 1.0
    assert scores["rmse"] == 1.0
    assert scores["mae_top10"] == 1.0
    assert set(scores) == {"mae", "rmse", "r2", "mae_top10"}
