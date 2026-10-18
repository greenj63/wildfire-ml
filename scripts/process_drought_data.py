# scripts/process_drought_data.py
import pandas as pd

from shared.data_loader import get_dataset_dir

DATASET_NAME = "droughts"
FILE_NAMES = [
    "train_timeseries.csv",
    "validation_timeseries.csv",
    "test_timeseries.csv",
]


def main() -> None:

    files = []
    for filename in FILE_NAMES:
        path = get_dataset_dir(DATASET_NAME) / filename
        if not path.exists():
            raise FileExistsError(f"path is not found: {path}")

        files.append(pd.read_csv(path))

    df = pd.concat(files, ignore_index=True)
    print(df.shape)
    print(df.head())

    # Save the trimmed data so everyone can use it without the big database
    out_dir = get_dataset_dir(DATASET_NAME, processed=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "drought_clean.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} rows to {out_path}")


if __name__ == "__main__":
    main()
