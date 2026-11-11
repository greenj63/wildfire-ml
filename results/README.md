# Results (committed)

Unlike `data/` and `models/`, this folder is in Git so anyone can check the comparison
without re-training.

| File | Made by | What it is |
|---|---|---|
| `comparison.csv` | `python -m scripts.compare_models` | One row per model: member, protocol, validation and test metrics (mean and std across seeds), chosen settings. |
| `metrics/<model>.json` | `python -m scripts.compare_models` | Each model's full `metrics.json`: search space, every setting tried, each seed's scores, package versions. |
| `error_analysis_summary.csv` | `python -m scripts.error_analysis` | One row per model: fast-fire ranking and alerting, underprediction of the fastest 10%. Needs the trained models in `models/`. |
| `error_analysis.csv` | `python -m scripts.error_analysis` | Test MAE by fire lifetime, fire size class, and state, for every model. |

`compare_models` reads `models/<name>/metrics.json` when you trained that model locally,
and otherwise the committed `metrics/<name>.json`, so every member's committed results
appear in the table. After retraining your model, rerun it and commit your
`metrics/<name>.json` and `comparison.csv`.

Metrics are on the log scale (`log(1 + acres per day)`); MAE is the primary metric. See
`docs/evaluation_plan.md`.
