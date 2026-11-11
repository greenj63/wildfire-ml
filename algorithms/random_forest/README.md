# Random Forest Regression

**Owner:** Erick Sanchez

## What it does
Predicts how fast a newly reported wildfire will spread (`log(1 + acres per day)`) with a
random forest: many decision trees trained on random samples of the fires and features,
whose predictions are combined. Trees can capture thresholds and interactions that a
linear model cannot, and the averaging over many trees makes the forest less prone to
overfitting than a single tree. It is the team's bagged-trees model, a direct comparison
with LightGBM's boosted trees.

The forest uses `criterion="absolute_error"`, so each tree splits to reduce absolute
error and predicts a leaf median. This aims the model at the median of the target, which
is the team's decision because the target is skewed (`docs/discussion_log.md`, entry 15)
and matches the MAE metric.

## Data
Uses the shared experiment (`docs/evaluation_plan.md`): target `log(1 + SPREAD_RATE)`,
the 42 features in `shared/experiment.py`, and the committed `train.csv.gz` (79,961
rows), `validation.csv.gz` (10,026), and `test.csv.gz` (10,013) in
`data/processed/wildfire_drought/`.
- Model-specific preprocessing: none. Only the shared pipeline (median fill, scaling,
  one-hot categories). Trees don't need scaling, but it doesn't hurt them, and it keeps
  the input identical to the other models.

## Settings
Library: scikit-learn `RandomForestRegressor` with `criterion="absolute_error"` and
`n_jobs=-1`. Every setting was chosen by validation MAE only (seed 0), over all 108
combinations of this grid:

| Setting | Values tried | Best |
|---|---|---|
| `max_depth` | 10, 20, `None` | **20** |
| `min_samples_leaf` | 2, 5, 10 | **10** |
| `min_samples_split` | 2, 10 | **2** |
| `n_estimators` | 100, 200 | **200** |
| `max_features` | 0.3, 0.5, `sqrt` | **0.5** |

`max_depth`, `min_samples_leaf`, and `min_samples_split` limit how closely each tree can
fit the training data, which reduces overfitting. `max_features` limits how many
features each split considers, which keeps the trees different from each other.
- **Final setting:** `max_depth=20`, `min_samples_leaf=10`, `min_samples_split=2`,
  `n_estimators=200`, `max_features=0.5`. The top two settings differ only in
  `min_samples_split` and tie on validation MAE (0.551).
- **Defaults not tuned:** `bootstrap=True` and everything else not listed above.
- **Seeds:** `0-4` (5 runs). Results vary slightly between seeds because of the random
  samples and feature choices.

## How to run (from the repo root)
```bash
python -m algorithms.random_forest.train
python -m algorithms.random_forest.predict
```
Then update the team table: `python -m scripts.compare_models`

Training is slow because of the absolute-error criterion: one final fit takes about 2.5
minutes on average, and the search runs 108 fits plus 2 fits per seed.

## Results
Mean ± standard deviation across 5 seeds. MAE and RMSE are on the log scale.

| Split | MAE (primary) | RMSE | R² | MAE, fastest 10% |
|---|---|---|---|---|
| Validation | 0.5513 ± 0.0004 | 1.1608 ± 0.0007 | 0.263 ± 0.001 | 2.862 ± 0.003 |
| Test | 0.5793 ± 0.0005 | 1.1983 ± 0.0010 | 0.247 ± 0.001 | 2.948 ± 0.005 |

Source: `results/comparison.csv` (random_forest row) and
`results/metrics/random_forest.json`.

## Notes
- **Versus the baseline** (training median; test MAE 0.711): 18.5% lower.
- **Versus LightGBM** (test MAE 0.565, R² 0.277): the forest is about 0.015 higher on MAE,
  more than the seed-to-seed spread of either model (about 0.0005 to 0.0008), but small
  in practice. On the fastest 10% of fires the two are tied (2.948 vs 2.947).
- **Search:** validation MAE ranges from 0.551 to 0.597 across the 108 settings, so the
  choice of settings matters more here than for the Huber model.
- **Package versions:** this run's metrics record Python 3.12.10 and pandas 3.1.1, while
  the other models' runs record 3.12.14 and 3.0.6 (scikit-learn is the same, 1.9.1). The
  differences should not change results, but note them in the reproducibility section.
- **Not yet done:** error analysis (fast fires, states, fire size) and feature
  importances.
- **Reproduced:** refitting the final setting once (seed 0, train + validation) gave
  test MAE 0.5797 (RMSE 1.1993, R² 0.246, fastest-10% 2.951), against the saved seed-0
  values 0.5786 / 1.1971 / 0.249 / 2.940. The 0.001 MAE gap is about twice the
  seed-to-seed standard deviation, so it is small but not exactly identical, possibly
  from the different package versions noted above.
- **`predict.py`** is the shared template with the current 42-feature example (it used
  to have the old 24 columns and failed with `KeyError: 'Aspect'`). Running it predicts
  0.1 acres/day for an example fire that actually spread 0.01 acres/day.

## Error analysis
Test set (10,013 fires), from `python -m scripts.error_analysis` (full tables in
`results/error_analysis.csv` and `results/error_analysis_summary.csv`). The model is the
final one, refit on train + validation. A fast fire spreads at least 11 acres/day (10.7%
of test fires). The group labels (lifetime, size class) are only used to slice the
errors; they are not features.

- **Fast fires are still underpredicted, but it ranks them well.** The 10% fastest fires
  have an actual median of 52.35 acres/day; the median prediction is 2.93, and 98.6% are
  underpredicted. As a ranking it is second only to LightGBM (ROC-AUC 0.797, PR-AUC
  0.406 vs 0.107 by chance). Flagging the 20% of fires with the highest predictions
  catches 62% of fast fires with precision 0.33.
- **By fire size class** (test MAE, baseline in brackets): A 0.144 (0.030), B 0.501
  (0.635), C 1.584 (2.552), D 2.605, E 3.271, F 4.216, G 5.636 (6.781). It has the best
  MAE of any model on class C, and is close to LightGBM on D–G.
- **By fire lifetime** (test MAE): 1–2 days 0.471 (0.590), 3–30 days 0.927 (1.116), 31–90
  days 1.308 (1.375), 91+ days 2.069 (1.980). It is the best model for 31–90 day fires,
  and the worst for 91+ days (38 test fires).
- **By state** (states with 200+ test fires): lowest in New York (0.25), Colorado (0.30),
  and Oregon (0.37); highest in Florida (0.99), Georgia (0.95), and Nevada (0.92).
- **Likely reason (not tested):** the `absolute_error` criterion aims each tree at the
  median, which is the typical (small) fire, so fast fires are underpredicted.
