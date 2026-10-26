# scripts/make_split.py
"""Write train.csv, validation.csv, and test.csv next to wildfire_drought.csv.

The files are committed, so normally nobody needs to run this. Only run it if the
combined dataset changes, and tell the group (every model must be re-run). The seed is
fixed, so the same data always gives the same split.
"""

from shared.data_loader import load_dataset
from shared.experiment import (
    DATASET_FILENAME,
    DATASET_NAME,
    SPLIT_GROUP_COLUMNS,
    make_split,
    split_path,
)


def main() -> None:
    df = load_dataset(
        DATASET_NAME, filename=DATASET_FILENAME, processed=True, low_memory=False
    )
    parts = make_split(df)

    for name, part in parts.items():
        path = split_path(name)
        part.to_csv(path, index=False)
        print(f"{name}: {len(part):,} rows ({len(part) / len(df):.1%}) -> {path}")

    # Sanity check: no county-day appears in more than one split
    keys = {
        name: set(map(tuple, part[SPLIT_GROUP_COLUMNS].to_numpy()))
        for name, part in parts.items()
    }
    assert not keys["train"] & keys["validation"]
    assert not keys["train"] & keys["test"]
    assert not keys["validation"] & keys["test"]


if __name__ == "__main__":
    main()
