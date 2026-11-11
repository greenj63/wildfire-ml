# Huber Regression

**Owner:** Jack Greene

## What it does
Predicts how fast a newly reported wildfire will spread (`log(1 + acres per day)`) with
Huber regression, a linear model with a robust loss. The loss is squared error for small
errors and absolute error for large ones, where `epsilon` sets the switch point. This
matters for the wildfire data because the target has extreme outliers (the median is
0.1 acres/day, the maximum about 65,000), and a plain linear regression would be pulled
toward them. It is the team's simple, interpretable linear model, so it shows how much
the tree and neighbor models gain from non-linear structure.

The team decided to aim every model at the median of the target, because the data is
skewed (`docs/discussion_log.md`, entry 15). With a small `epsilon` the Huber loss is
mostly absolute error, so it sits between median and mean regression; it is not a pure
median model like LightGBM's `l1` objective.

## Data
Uses the shared experiment (`docs/evaluation_plan.md`): target `log(1 + SPREAD_RATE)`,
the 42 features in `shared/experiment.py`, and the committed `train.csv.gz` (79,961
rows), `validation.csv.gz` (10,026), and `test.csv.gz` (10,013) in
`data/processed/wildfire_drought/`. The features cover location, timing, the drought
score, terrain, vegetation, weather and fire-danger indices at the ignition point, land
owner, reporting agency, nearby fire stations, ecoregion, and population (most from FPA
FOD-Attributes, Pourmohamad et al., 2024).
- Model-specific preprocessing: none. Only the shared pipeline (median fill, scaling,
  one-hot categories). Scaling matters here, since the penalty on the coefficients
  treats all features alike.

## Settings
Library: scikit-learn `HuberRegressor`. Every setting was chosen by validation MAE only.

| Setting | Values tried | Best | Why |
|---|---|---|---|
| `epsilon` | 1.0, 1.1, 1.15, 1.25, 1.35 | **1.1** | Where the loss switches from squared to absolute error. Values near the minimum (1.0) are the most robust to outliers. |
| `alpha` | 1e-6, 1e-4, 1e-2, 1 | **1e-4** | Strength of the L2 penalty on the coefficients. With 80K rows and 42 features (more after one-hot), little shrinkage is needed. |

- **Final setting:** `epsilon=1.1`, `alpha=0.0001` (all 20 combinations tried).
- **Defaults not tuned:** `max_iter=500` (set in `model.py` so the optimizer converges),
  everything else.
- **Seeds:** one run (`SEEDS = [0]`). Huber regression is deterministic (an L-BFGS
  optimizer with no random steps), so more seeds would give identical results and the
  standard deviation is not applicable.

## How to run (from the repo root)
```bash
python -m algorithms.huber-regression.train
python -m algorithms.huber-regression.predict
```
Then update the team table: `python -m scripts.compare_models`

## Results
One run (seed 0). MAE and RMSE are on the log scale. Fit time on a laptop CPU is about
4 seconds (it varies by machine).

| Split | MAE (primary) | RMSE | R² | MAE, fastest 10% |
|---|---|---|---|---|
| Validation | 0.5905 | 1.2838 | 0.099 | 3.366 |
| Test | 0.6215 | 1.3248 | 0.080 | 3.502 |

Source: `results/comparison.csv` (huber-regression row) and
`results/metrics/huber-regression.json`.

## Notes
- **The settings barely matter.** Validation MAE across all 20 combinations ranges from
  0.5905 to 0.5952. The best setting beats the next best by about 0.0001, far less than
  a difference worth reporting. For every `alpha`, `epsilon=1.1` is lowest, 1.0 and 1.15
  are slightly worse, and MAE rises steadily from 1.25 to 1.35. `alpha` has almost no
  effect (under 0.0002 between values). Treat `epsilon=1.1` as a reasonable choice, not
  a clear winner.
- **Versus the baseline** (training median; validation 0.681, test 0.711): validation
  MAE is 13% lower and test MAE 12.5% lower. It improves on the baseline but is the
  weakest of the four learned models (LightGBM 0.565, random forest 0.579, KNN 0.606 on
  test).
- **Low R²:** about 0.08 to 0.10. A linear model explains only a small share of the
  variance, so the gain over the baseline is real but the predictions are coarse.
- **Fast fires are the weak spot.** The MAE on the fastest 10% of fires (3.502 on test)
  is about 5.6 times the overall MAE, and only slightly better than the baseline's 4.257.
- **Protocol:** tuned on validation; the test score comes from a model refit on train +
  validation, as recorded in `comparison.csv`.
- **Negative predictions are rare and small.** On the test set, 46 of 10,013 predictions
  (0.46%) fall below 0 on the log scale (lowest −0.108, about −0.10 acres/day after
  `expm1`). Clipping them at 0 changes test MAE from 0.6215 to 0.6214, so it makes no
  practical difference. `predict()` could still clip at 0 so it never returns a
  negative spread rate.
- **`predict.py`** is the shared version with the current 42-feature example. Running
  it predicts 0.091 acres/day for the example fire (actual 0.01).

## Error analysis
Test set (10,013 fires), from `python -m scripts.error_analysis` (full tables in
`results/error_analysis.csv` and `results/error_analysis_summary.csv`). The model is the
final one, refit on train + validation. A fast fire spreads at least 11 acres/day (10.7%
of test fires). The group labels (lifetime, size class) are only used to slice the
errors; they are not features.

- **Fast fires are barely caught.** The 10% fastest fires have an actual median of 52.35
  acres/day; the median prediction is 1.27, and 99.6% are underpredicted. As a ranking it
  is the weakest of the four learned models (ROC-AUC 0.778, PR-AUC 0.306 vs 0.107 by
  chance). Flagging the 20% of fires with the highest predictions catches 52% of fast
  fires with precision 0.28 (random flagging would give 20% and 0.11).
- **By fire size class** (test MAE, baseline in brackets): A 0.122 (0.030), B 0.470
  (0.635), C 1.912 (2.552), D 3.116, E 3.813, F 4.892, G 6.367 (6.781). It trades
  accuracy on the tiniest fires for gains on everything from class B up, but the gains on
  large fires are the smallest of any learned model.
- **By fire lifetime** (test MAE): 1–2 days 0.500 (0.590), 3–30 days 1.022 (1.116), 31–90
  days 1.351 (1.375), 91+ days 2.014 (1.980). It improves on the baseline up to a month,
  and is no better for the longest fires (38 test fires).
- **By state** (states with 200+ test fires): lowest in New York (0.29), Colorado (0.32),
  and Washington (0.36), where it is no better than the baseline; highest in Florida
  (1.09), Georgia (1.04), and Nevada (0.98).
- **Likely reason (not tested):** a linear model cannot represent thresholds and
  interactions, so its predictions stay close to the typical small fire (R² 0.08). Only
  0.5% of its predictions go below 0 (see above).
