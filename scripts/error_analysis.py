# scripts/error_analysis.py
"""Error analysis of every trained model on the same test fires.

Run after training (from the repo root):  python -m scripts.error_analysis

Loads models/<name>/model.joblib for each model (the seed-0 model refit on train +
validation) and scores it on the test split. Nothing is tuned here, so the test set is
only looked at, not used to choose anything. Writes (both committed):
    results/error_analysis_summary.csv   one row per model
    results/error_analysis.csv           test MAE by group (lifetime, fire size, state)

"Fast fire" means a true spread rate of at least FAST_ACRES_PER_DAY. Detection is
scored by how well the predicted spread rate ranks fires (ROC-AUC, PR-AUC), and by
flagging the fires with the highest predicted spread rates at a fixed alert rate, so no
cut-off has to be chosen on any data.
"""

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from shared.experiment import (
    FEATURES,
    TARGET_COLUMN,
    add_derived_columns,
    split_path,
)
from shared.utils import get_project_root, load_model

FAST_ACRES_PER_DAY = 11
ALERT_RATE = 0.20  # flag the 20% of fires with the highest predicted spread rate
MIN_STATE_FIRES = 200
LIFETIME_BINS = [0, 2, 30, 90, np.inf]
LIFETIME_LABELS = ["1-2 days", "3-30 days", "31-90 days", "91+ days"]


def load_test() -> pd.DataFrame:
    return add_derived_columns(pd.read_csv(split_path("test"), low_memory=False))


def group_mae(test: pd.DataFrame, error: np.ndarray, groups: pd.Series, name: str):
    """Rows of (breakdown, group, n, mae) for one model, one grouping."""
    frame = pd.DataFrame({"group": groups.astype(str).values, "error": error})
    for group, part in frame.groupby("group", observed=True):
        yield {
            "breakdown": name,
            "group": group,
            "n": len(part),
            "mae": float(part["error"].mean()),
        }


def analyse(name: str, test: pd.DataFrame) -> tuple[dict, list[dict]]:
    pred = load_model(name).predict(test[FEATURES])
    y = test[TARGET_COLUMN].to_numpy()
    error = np.abs(y - pred)
    fast = (test["SPREAD_RATE"] >= FAST_ACRES_PER_DAY).to_numpy()

    # Alert: the top ALERT_RATE share of fires by predicted spread rate
    flagged = pred >= np.quantile(pred, 1 - ALERT_RATE)
    # The 10% fastest fires (same definition as mae_top10)
    top10 = y >= np.quantile(y, 0.9)

    # A model that predicts the same value for every fire has no ranking to score
    constant = np.ptp(pred) == 0
    caught = (flagged & fast).sum()
    summary = {
        "model": name,
        "test_mae": float(error.mean()),
        "fast_fire_share": float(fast.mean()),
        "fast_roc_auc": np.nan if constant else float(roc_auc_score(fast, pred)),
        "fast_pr_auc": (
            np.nan if constant else float(average_precision_score(fast, pred))
        ),
        "alert_rate": ALERT_RATE,
        # Flagging "the top 20%" means nothing when every prediction is the same
        "fast_recall_at_alert": np.nan if constant else float(caught / fast.sum()),
        "fast_precision_at_alert": (
            np.nan if constant else float(caught / max(flagged.sum(), 1))
        ),
        "top10_actual_median_acres_day": float(np.median(np.expm1(y[top10]))),
        "top10_predicted_median_acres_day": float(np.median(np.expm1(pred[top10]))),
        "top10_share_underpredicted": float((pred[top10] < y[top10]).mean()),
        "share_negative_predictions": float((pred < 0).mean()),
    }

    rows = []
    lifetime = pd.cut(test["DURATION_DAYS"], LIFETIME_BINS, labels=LIFETIME_LABELS)
    rows += group_mae(test, error, lifetime, "fire lifetime")
    rows += group_mae(test, error, test["FIRE_SIZE_CLASS"], "fire size class")
    big_states = test["STATE"].value_counts()
    big_states = big_states[big_states >= MIN_STATE_FIRES].index
    in_big = test["STATE"].isin(big_states).to_numpy()
    rows += group_mae(test[in_big], error[in_big], test.loc[in_big, "STATE"], "state")
    for row in rows:
        row["model"] = name
    return summary, rows


def main() -> None:
    root = get_project_root()
    names = sorted(p.parent.name for p in (root / "models").glob("*/model.joblib"))
    if not names:
        print("No trained models found. Run python -m algorithms.<name>.train first.")
        return

    test = load_test()
    print(f"{len(test)} test fires; fast = at least {FAST_ACRES_PER_DAY} acres/day")
    summaries, rows = [], []
    for name in names:
        summary, group_rows = analyse(name, test)
        summaries.append(summary)
        rows += group_rows

    out_dir = root / "results"
    summary_table = pd.DataFrame(summaries).sort_values("test_mae")
    summary_table.to_csv(out_dir / "error_analysis_summary.csv", index=False)
    groups = pd.DataFrame(rows)[["model", "breakdown", "group", "n", "mae"]]
    groups.to_csv(out_dir / "error_analysis.csv", index=False)

    with pd.option_context("display.width", 220, "display.max_columns", None):
        print(summary_table.round(3).to_string(index=False))
    print("Saved results/error_analysis_summary.csv and results/error_analysis.csv")


if __name__ == "__main__":
    main()
