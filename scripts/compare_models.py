# scripts/compare_models.py
"""Build the team's comparison table from every model's metrics.json.

Run after training (from the repo root):  python -m scripts.compare_models

Writes (both committed, so the results can be checked without re-training):
    results/comparison.csv           one row per model, validation and test separate
    results/metrics/<model>.json     each model's full settings and results
"""

import json
import shutil

import pandas as pd

from shared.utils import get_project_root

METRICS = ["mae", "rmse", "r2", "mae_top10"]


def main() -> None:
    root = get_project_root()
    results_dir = root / "results"
    copies_dir = results_dir / "metrics"
    copies_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for path in sorted((root / "models").glob("*/metrics.json")):
        metrics = json.loads(path.read_text())
        if "test" not in metrics or "mae" not in metrics["test"]:
            print(f"Skipping {path} (not from the shared train.py)")
            continue
        shutil.copy(path, copies_dir / f"{metrics['algorithm']}.json")

        row = {
            "model": metrics["algorithm"],
            "member": metrics["member"],
            "protocol": (
                f"{metrics['split']}; tuned on validation; "
                "test model refit on train+validation"
            ),
            "runs": len(metrics["seeds"]),
            "best_params": json.dumps(metrics["best_params"]),
        }
        for part in ["validation", "test"]:
            for metric in METRICS:
                row[f"{part}_{metric}_mean"] = metrics[part][metric]["mean"]
                row[f"{part}_{metric}_std"] = metrics[part][metric]["std"]
        row["fit_seconds_mean"] = metrics["fit_seconds_mean"]
        rows.append(row)

    if not rows:
        print("No trained models found. Run python -m algorithms.<name>.train first.")
        return

    table = pd.DataFrame(rows).sort_values("validation_mae_mean")
    out_path = results_dir / "comparison.csv"
    table.to_csv(out_path, index=False)

    with pd.option_context("display.width", 200, "display.max_columns", None):
        print(
            table[
                ["model", "member", "runs", "validation_mae_mean", "test_mae_mean"]
                + ["test_mae_std", "test_mae_top10_mean"]
            ].to_string(index=False)
        )
    print(f"Saved {len(table)} models to {out_path}")


if __name__ == "__main__":
    main()
