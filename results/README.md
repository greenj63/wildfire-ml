# Results (committed)

Unlike `data/` and `models/`, this folder is in Git so anyone can check the comparison
without re-training.

| File | Made by | What it is |
|---|---|---|
| `comparison.csv` | `python -m scripts.compare_models` | One row per model: member, protocol, validation and test metrics (mean and std across seeds), chosen settings. |
| `metrics/<model>.json` | `python -m scripts.compare_models` | Each model's full `metrics.json`: search space, every setting tried, each seed's scores, package versions. |

Metrics are on the log scale (`log(1 + acres per day)`); MAE is the primary metric. See
`docs/evaluation_plan.md`.
