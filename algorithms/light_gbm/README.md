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
the 42 features in `shared/experiment.py`, and the committed `train.csv.gz` (79,961
rows), `validation.csv.gz` (10,026), and `test.csv.gz` (10,013) in
`data/processed/wildfire_drought/`. The features cover location, timing, the drought
score, terrain, vegetation, weather and fire-danger indices at the ignition point, land
owner, reporting agency, nearby fire stations, ecoregion, and population (most from FPA
FOD-Attributes, Pourmohamad et al., 2024).
- Model-specific preprocessing: none. Only the shared pipeline (median fill, scaling,
  one-hot categories). Trees don't need scaling, but it doesn't hurt them, and it keeps
  the input identical to the other models.

## Settings
Library: `lightgbm` 4.7.0, using `LGBMRegressor` (scikit-learn interface).

Every setting was chosen by validation MAE only; the test set was never used to choose
settings. Stages 1 and 2 ran on the original 24 features; stage 3 reran the stage 2
search on the current 42 features.

**Stage 1** (54 combinations, LightGBM's default 100 trees, original features; full
results in `tuning/stage1_metrics.json`):

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

**Stage 2** (16 combinations, the current `PARAM_GRID`, original features; results in
`tuning/stage2_metrics_old_features.json`): `objective="l1"` and `min_child_samples=50`
were fixed from stage 1. `n_estimators` was raised to 500, because the best
`learning_rate` and `num_leaves` were at the top of their stage 1 ranges, which
suggested 100 trees was too few. Row and feature sampling were added. Best validation
MAE 0.5705, essentially the same as stage 1 (0.5706).

**Stage 3** (the same 16 combinations, current 42 features):

| Setting | Values tried | Best (stage 2 → stage 3) |
|---|---|---|
| `num_leaves` | 63, 127 | 127 → **63** |
| `learning_rate` | 0.05, 0.1 | 0.05 → **0.05** |
| `subsample` | 0.8, 1.0 | 1.0 → **1.0** |
| `colsample_bytree` | 0.8, 1.0 | 0.8 → **0.8** |

Best validation MAE 0.5411. The top 4 settings are within 0.0005 of each other, and
every setting with `learning_rate=0.05` beat every setting with 0.1. With the richer
features, smaller trees (63 leaves) are enough.

- **Final setting:** `objective="l1"`, `n_estimators=500`, `num_leaves=63`,
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

Training runs 26 fits (16 for tuning, then 2 per seed), about 7 seconds each on a
laptop CPU, so roughly 3 minutes in total.

## Results
Mean ± standard deviation across 5 seeds. MAE and RMSE are on the log scale.

| Split | MAE (primary) | RMSE | R² | MAE, fastest 10% |
|---|---|---|---|---|
| Validation | 0.5413 ± 0.0009 | 1.1518 ± 0.0022 | 0.275 ± 0.003 | 2.893 ± 0.012 |
| Test | **0.5648 ± 0.0008** | 1.1749 ± 0.0025 | 0.277 ± 0.003 | **2.947 ± 0.020** |

**Compared with the baseline** (always predicts the training median; test MAE 0.711,
fastest-10% MAE 4.257): LightGBM is **20.5% lower on MAE** and **30.8% lower on the
fastest fires**.

**Compared with the original 24 features** (same model, same search):

| Test metric | Original features | Current features | Change |
|---|---|---|---|
| MAE | 0.5910 | 0.5648 | −0.026 (−4.4%) |
| R² | 0.192 | 0.277 | +0.085 |
| MAE, fastest 10% | 3.197 | 2.947 | −0.250 |
| Fast-fire ROC-AUC | 0.806 | 0.837 | +0.031 |
| Fast-fire PR-AUC | 0.379 | 0.443 | +0.064 |

## Notes
Error analysis on the test set, using the final model (seed 0, trained on train +
validation).

- **Detecting fast fires** (spread ≥ 11 acres/day, 10.7% of test fires): ranking is
  good (ROC-AUC 0.837, PR-AUC 0.443 vs 0.107 by chance). Taken at face value, the
  prediction catches only 16% of fast fires (precision 0.65). With an alert cut-off
  chosen on validation (predicted ≥ 1.9 acres/day), it catches 55% (595 of 1,074) with
  precision 0.40, F1 0.47, F2 0.52. Accuracy is about 0.86–0.90 either way, close to
  the 0.89 of never predicting "fast", so it isn't a useful measure here.
- **Fast fires are still badly underpredicted.** For the 10% fastest test fires, the
  actual median is 52.3 acres/day, but the model's median prediction is 2.64 acres/day
  (up from 1.64 with the original features). 98.2% of them are underpredicted. The `l1`
  objective aims at the typical fire, which is small. This is the main weakness for a
  responder use case.
- **By fire lifetime** (test MAE, baseline in brackets): ≤ 2 days 0.457 (0.590),
  3–30 days 0.901 (1.116), 31–90 days 1.332 (1.375), ≥ 91 days 2.041 (1.980). The model
  is clearly better than the baseline for fires lasting up to a month, about the same
  for 31–90 days, and no better for the longest fires (only 38 test fires).
- **Error grows with fire size class** (test MAE): A 0.13, B 0.48, C 1.63, D 2.58,
  E 3.25, F 4.08, G 5.54.
- **Error varies by state** (test MAE, states with 200+ test fires): lowest in New York
  (0.24), Colorado (0.30), and Oregon (0.36); highest in Florida (0.99), Georgia (0.95),
  and Nevada (0.85).
- **Most important features** (share of total split gain, one-hot categories summed):
  longitude 15.3%, latitude 7.8%, state 4.2%, elevation 4.1%, discovery hour 3.6%,
  ecoregion 3.4%, minimum humidity 3.0%, day of year 3.0%, population 2.6%, land owner
  2.6%, precipitation 2.6%, solar radiation 2.5%. Location still matters most.
- **Ideas:** a `huber` or `l2` objective, or a lower alert cut-off, would catch more fast
  fires at the cost of overall MAE. The team's median-vs-mean decision
  (`docs/discussion_log.md`, entry 15) applies here too.
