"""Cleaning steps that more than one algorithm needs."""

import pandas as pd


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
