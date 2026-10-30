# LightGBM

**Owner:** Arlim Macaldo

## What it does
Predicts how fast a newly reported wildfire will spread (`log(1 + acres per day)`) using
LightGBM, a gradient-boosted decision tree model. Trees can pick up thresholds and
interactions (for example, wind only mattering when it's dry) that a linear model
can't, and LightGBM trains quickly on CPU. It shows how much a strong non-linear model
gains over the baseline and simpler models.

## Data
Uses the shared experiment (`docs/evaluation_plan.md`): target `log(1 + SPREAD_RATE)`,
features from `shared/experiment.py`, and the committed `train.csv` (79,961 rows),
`validation.csv` (10,026), and `test.csv` (10,013) in
`data/processed/wildfire_drought/`.
- Model-specific preprocessing: none. Only the shared pipeline (median fill, scaling,
  one-hot `STATE`). Trees don't need scaling, but it doesn't hurt them, and it keeps the
  input identical to the other models.

## Settings
Library: `lightgbm` 4.7.0, using `LGBMRegressor` (scikit-learn interface).

Tuned in two stages, each selected by validation MAE only (the test set was never used
to choose settings).

**Stage 1** (54 combinations, LightGBM's default 100 trees; full results in
`tuning/stage1_metrics.json`):

| Setting | Values tried | Best |
|---|---|---|
| `objective` | `l2`, `l1`, `huber` | `l1` |
| `num_leaves` | 15, 31, 63 | 63 |
| `learning_rate` | 0.03, 0.05, 0.1 | 0.1 |
| `min_child_samples` | 20, 50 | 50 |

The objective mattered most. Best validation MAE for each: `l1` 0.5706, `huber`
0.6115, `l2` 0.6790. `l1` trains on absolute error, the same thing the team's primary
metric measures. Most fires sit near the median (0.1 acres/day), which absolute error
rewards and squared error doesn't.

**Stage 2** (16 combinations, the current `PARAM_GRID`): `objective="l1"` and
`min_child_samples=50` were fixed from stage 1. `n_estimators` was raised to 500,
because the best `learning_rate` and `num_leaves` were at the top of their stage 1
ranges, which suggested 100 trees was too few. Row and feature sampling were added.

| Setting | Values tried | Best |
|---|---|---|
| `num_leaves` | 63, 127 | 127 |
| `learning_rate` | 0.05, 0.1 | 0.05 |
| `subsample` | 0.8, 1.0 | 1.0 |
| `colsample_bytree` | 0.8, 1.0 | 0.8 |

Best validation MAE in stage 2 was 0.5705, essentially the same as stage 1 (0.5706), so
tuning stopped here. The top 4 stage 2 settings are within 0.0007 of each other.

- **Final setting:** `objective="l1"`, `n_estimators=500`, `num_leaves=127`,
  `learning_rate=0.05`, `min_child_samples=50`, `subsample=1.0`, `subsample_freq=1`,
  `colsample_bytree=0.8`.
- **Defaults not tuned:** `max_depth` (unlimited; `num_leaves` controls size instead),
  `reg_alpha`, `reg_lambda`, and everything else.
- **Seeds:** `0-4` (5 runs). Results vary slightly between seeds because
  `colsample_bytree=0.8` samples features randomly.

## How to run (from the repo root)
```bash
python -m algorithms.light_gbm.train
python -m algorithms.light_gbm.predict
```
Then update the team table: `python -m scripts.compare_models`

Training runs 26 fits (16 for tuning, then 2 per seed). On a laptop CPU, our runs took
between about 6 and 22 minutes, depending on what else the machine was doing.

## Results
Mean ± standard deviation across 5 seeds. MAE and RMSE are on the log scale.

| Split | MAE (primary) | RMSE | R² | MAE, fastest 10% |
|---|---|---|---|---|
| Validation | 0.5713 ± 0.0012 | 1.2260 ± 0.0021 | 0.178 ± 0.003 | 3.153 ± 0.008 |
| Test | 0.5910 ± 0.0010 | 1.2416 ± 0.0020 | 0.192 ± 0.003 | 3.197 ± 0.004 |

For reference, predicting the training median for every fire gives a test MAE of about
0.71 and a fastest-10% MAE of about 4.26. LightGBM is about 17% lower on MAE and 25%
lower on the fastest fires.

## Notes
- **Fast fires are badly underpredicted.** For the 10% fastest-spreading test fires, the
  actual median is 52.3 acres/day, but the model's median prediction is 1.64 acres/day.
  98.5% of them are underpredicted. The `l1` objective aims at the typical fire, which
  is small, so the model plays it safe. This is the main weakness for a responder use
  case.
- **Error grows with fire size class** (test MAE): A 0.13, B 0.47, C 1.73, D 2.85,
  E 3.55, F 4.48, G 5.88.
- **Error varies by state** (test MAE, states with 200+ test fires): lowest in New York
  (0.25), Colorado (0.30), and Washington (0.35); highest in Florida (1.06), Georgia
  (0.97), and Nevada (0.93).
- **Most important features** (share of total split gain): longitude 13.8%, latitude
  8.7%, surface pressure 6.8%, precipitation 5.2%, day of year 4.9%, daily temperature
  range 4.3%, discovery hour 4.2%, drought score 4.1%. Location matters most, possibly
  standing in for regional vegetation and response practices.
- **Ideas:** a `huber` or `l2` objective, or a model trained only on large fires, could
  reduce underprediction of fast fires at the cost of overall MAE. That trade-off is
  worth discussing as a team.
