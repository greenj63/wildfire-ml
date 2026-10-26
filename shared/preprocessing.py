"""Cleaning steps that more than one algorithm needs.

For the shared experiment, use build_preprocessor(). The older helpers below compute
their statistics on whatever data you pass them, so using them before the split leaks
test data into training.
"""

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from shared.experiment import CATEGORICAL_FEATURES, NUMERIC_FEATURES


def build_preprocessor() -> ColumnTransformer:
    """Shared, leak-free preprocessing for the experiment features.

    Numbers: fill gaps with the median, then scale. STATE: one-hot encoding.
    It's part of each model's Pipeline, so it's only ever fitted on training data.
    """
    numeric = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]
    )
    categorical = OneHotEncoder(handle_unknown="ignore")
    return ColumnTransformer(
        [
            ("numeric", numeric, NUMERIC_FEATURES),
            ("categorical", categorical, CATEGORICAL_FEATURES),
        ]
    )


def fill_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Fill numeric gaps with the median and text gaps with the most common value."""
    df = df.copy()
    for column in df.columns:
        if df[column].isna().any():
            if pd.api.types.is_numeric_dtype(df[column]):
                df[column] = df[column].fillna(df[column].median())
            else:
                df[column] = df[column].fillna(df[column].mode().iloc[0])
    return df


def encode_categories(df: pd.DataFrame) -> pd.DataFrame:
    """Turn text columns into 0/1 columns (one-hot encoding)."""
    return pd.get_dummies(df, drop_first=True)


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Scale numeric columns to mean 0 and standard deviation 1."""
    df = df.copy()
    numeric = df.select_dtypes(include="number").columns
    std = df[numeric].std().replace(0, 1)
    df[numeric] = (df[numeric] - df[numeric].mean()) / std
    return df
