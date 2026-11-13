"""Pull live data, build a sample, and predict spread rate with a trained model.

Run from the repo root (with .venv active):

    python -m backend.live_predict                       # newest fires from NIFC WFIGS
    python -m backend.live_predict --hours 72 --limit 10
    python -m backend.live_predict --point 38.56 -119.91 --when "2026-11-10 18:00"
    python -m backend.live_predict --sample data/processed/live_samples/<file>.csv

The sample (model inputs plus notes on missing data) is saved to
data/processed/live_samples/ so it can be re-scored later. It is never added to the
training split. Predictions are acres per day; the model was trained on fires
from 2000-2020, so treat them as rough.
"""

import argparse
import importlib
import sys
from datetime import UTC, datetime

import pandas as pd

from backend.live.sample import META_COLUMNS, MODEL_COLUMNS, build_sample
from backend.live.wfigs import Fire, fetch_recent_fires
from shared.data_loader import get_dataset_dir

DEFAULT_ALGORITHM = "light_gbm"  # best model in results/comparison.csv
SAMPLE_DATASET = "live_samples"
PREDICTION_COLUMN = "PREDICTED_SPREAD_RATE_ACRES_PER_DAY"


def load_predictor(algorithm: str):
    """The algorithm's predict(input_data) -> acres per day."""
    return importlib.import_module(f"algorithms.{algorithm}.predict").predict


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--algorithm", default=DEFAULT_ALGORITHM, help="folder in algorithms/"
    )
    parser.add_argument(
        "--hours", type=int, default=24, help="look back this many hours"
    )
    parser.add_argument("--limit", type=int, default=3, help="most fires to score")
    parser.add_argument(
        "--point",
        nargs=2,
        type=float,
        metavar=("LAT", "LON"),
        help="score one location",
    )
    parser.add_argument(
        "--when", help='UTC discovery time for --point, "YYYY-MM-DD HH:MM"'
    )
    parser.add_argument(
        "--sample", help="score a saved sample CSV instead of pulling data"
    )
    parser.add_argument(
        "--skip-percentiles",
        action="store_true",
        help="skip the slow gridMET history pull (percentiles become missing)",
    )
    parser.add_argument(
        "--with-ndvi",
        action="store_true",
        help="add MODIS NDVI (only loosely matches training)",
    )
    return parser.parse_args(argv)


def collect_samples(args: argparse.Namespace) -> pd.DataFrame:
    if args.point:
        when = (
            datetime.strptime(args.when, "%Y-%m-%d %H:%M").replace(tzinfo=UTC)
            if args.when
            else datetime.now(UTC)
        )
        fires = [Fire("CUSTOM POINT", args.point[0], args.point[1], when)]
    else:
        fires = fetch_recent_fires(args.hours, args.limit)
    if not fires:
        sys.exit(f"No new wildfires reported in the last {args.hours} hours.")
    rows = []
    for number, fire in enumerate(fires, start=1):
        print(
            f"[{number}/{len(fires)}] {fire.name} ({fire.latitude:.4f}, "
            f"{fire.longitude:.4f})"
        )
        rows.append(build_sample(fire, args.skip_percentiles, args.with_ndvi))
    return pd.DataFrame(rows, columns=MODEL_COLUMNS + META_COLUMNS)


def save_csv(df: pd.DataFrame, prefix: str, stamp: str):
    folder = get_dataset_dir(SAMPLE_DATASET, processed=True)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{prefix}_{stamp}.csv"
    df.to_csv(path, index=False)
    return path


def main(argv=None) -> None:
    args = parse_args(argv)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    if args.sample:
        sample = pd.read_csv(args.sample)
    else:
        sample = collect_samples(args)
        print(f"Saved sample: {save_csv(sample, 'live_sample', stamp)}")

    try:
        predict = load_predictor(args.algorithm)
        records = sample[MODEL_COLUMNS].to_dict("records")
        predictions = [predict(record) for record in records]
    except FileNotFoundError as error:  # model not trained on this computer yet
        sys.exit(str(error))
    result = sample.assign(MODEL=args.algorithm, **{PREDICTION_COLUMN: predictions})
    print(f"Saved predictions: {save_csv(result, 'live_predictions', stamp)}\n")

    for _, row in result.iterrows():
        print(f"{row['FIRE_NAME']}  discovered {row['DISCOVERY_UTC']} UTC")
        rate = row[PREDICTION_COLUMN]
        print(f"  predicted spread rate: {rate:.2f} acres/day ({args.algorithm})")
        if pd.notna(row["REPORTED_ACRES"]):
            print(f"  reported size so far:  {row['REPORTED_ACRES']:.1f} acres")
        print(f"  weather date {row['WEATHER_DATE']}, drought map {row['SCORE_DATE']}")
        if isinstance(row["MISSING_FEATURES"], str) and row["MISSING_FEATURES"]:
            print(f"  missing inputs (filled by the model): {row['MISSING_FEATURES']}")
        if isinstance(row["WARNINGS"], str) and row["WARNINGS"]:
            print(f"  warnings: {row['WARNINGS']}")


if __name__ == "__main__":
    main()
