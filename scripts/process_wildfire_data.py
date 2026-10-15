# scripts/process_wildfire_data.py
import sqlite3
from contextlib import closing

import pandas as pd

from shared.data_loader import get_dataset_dir

DATASET_NAME = "wildfire"
DB_FILENAME = "FPA_FOD_20221014.sqlite"

# TODO: replace with the columns you actually need (check df.columns below)
COLUMNS_TO_KEEP = [
    "FIRE_NAME",
    "FIRE_YEAR",
    "DISCOVERY_DATE",
    "DISCOVERY_DOY",
    "DISCOVERY_TIME",
    "NWCG_CAUSE_CLASSIFICATION",
    "NWCG_GENERAL_CAUSE",
    "NWCG_CAUSE_AGE_CATEGORY",
    "CONT_DATE",
    "CONT_DOY",
    "CONT_TIME",
    "FIRE_SIZE",
    "FIRE_SIZE_CLASS",
    "LATITUDE",
    "LONGITUDE",
    "STATE",
    "COUNTY",
]


def main() -> None:
    db_path = get_dataset_dir(DATASET_NAME) / DB_FILENAME
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    with closing(sqlite3.connect(db_path)) as conn:
        # Peek at the columns first (cheap: only 5 rows)
        preview = pd.read_sql_query("SELECT * FROM Fires LIMIT 5;", con=conn)
        print(preview.columns.tolist())

        # Load only what you need
        query = f"SELECT {', '.join(COLUMNS_TO_KEEP)} FROM Fires;"
        df = pd.read_sql_query(query, con=conn)

    print(df.shape)
    print(df.head())

    # Save the trimmed data so everyone can use it without the big database
    out_dir = get_dataset_dir(DATASET_NAME, processed=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "wildfire_clean.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} rows to {out_path}")


if __name__ == "__main__":
    main()
