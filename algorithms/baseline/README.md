# Baseline (training median)

**Owner:** Arlim Macaldo

## What it does
Predicts the same spread rate for every fire: the median of the training target,
`log(1 + 0.1 acres/day)` = 0.0953. It ignores every feature. Every other model must beat
it to show that location, weather, terrain, and the rest actually help.

The median, not the mean, because the median is the best single constant under MAE,
the team's primary metric. It's the strongest possible "no information" prediction for
this metric, so beating it is a fair test.

## Data
Uses the shared experiment (`docs/evaluation_plan.md`): target `log(1 + SPREAD_RATE)`,
and the committed `train.csv.gz`, `validation.csv.gz`, and `test.csv.gz` in
`data/processed/wildfire_drought/`. Features are loaded but not used.
- Model-specific preprocessing: none. The shared pipeline still runs, but the model
  ignores its output.

## Settings
- Library: scikit-learn `DummyRegressor(strategy="median")`.
- `PARAM_GRID`: empty. There is nothing to tune.
- Seeds: one run (`SEEDS = [0]`). The baseline has no randomness, so more runs would
  give identical results.

## How to run (from the repo root)
```bash
python -m algorithms.baseline.train
python -m algorithms.baseline.predict
```
Then update the team table: `python -m scripts.compare_models`

Training takes a few seconds.

## Results
One run. MAE and RMSE are on the log scale (`log(1 + acres per day)`).

| Split | MAE (primary) | RMSE | R² | MAE, fastest 10% |
|---|---|---|---|---|
| Validation | 0.6814 | 1.5019 | −0.234 | 4.149 |
| Test | 0.7106 | 1.5410 | −0.245 | 4.257 |

The prediction (0.1 acres/day) is exactly right for the typical fire: 55% of fires are
contained the day they start. The negative R² shows it explains none of the
differences between fires.

## Notes
- The baseline always predicts 0.1 acres/day, so it never flags a fast fire: recall 0
  on fast fires (spread ≥ 11 acres/day). Its accuracy at "is this a fast fire?" is still
  about 89%, because 89% of fires are slow. This is why accuracy isn't used to compare
  models.
- Validation is easier than test for every model, including this one (0.681 vs 0.711),
  so the gap between them isn't a sign of overfitting.

## Error analysis
Test set (10,013 fires), from `python -m scripts.error_analysis` (full tables in
`results/error_analysis.csv` and `results/error_analysis_summary.csv`). The model is the
final one, refit on train + validation. A fast fire spreads at least 11 acres/day (10.7%
of test fires). The group labels (lifetime, size class) are only used to slice the
errors; they are not features.

- **Fastest fires:** the 10% fastest test fires have an actual median of 52.35 acres/day.
  The baseline predicts 0.1 for every one of them (100% underpredicted). It has no
  ranking, so ROC-AUC, PR-AUC, and alerting are not defined for it.
- **By fire size class** (test MAE): A 0.030, B 0.635, C 2.552, D 3.844, E 4.439, F 5.463,
  G 6.781. It is the *best* model on the tiniest fires (class A, 56% of the test set),
  where 0.1 acres/day is almost exactly right, and the worst on everything larger.
- **By fire lifetime** (test MAE): 1–2 days 0.590, 3–30 days 1.116, 31–90 days 1.375,
  91+ days 1.980 (38 fires). It is the best model for 91+ day fires: the learned models
  score 1.99 to 2.07 there.
- **By state** (states with 200+ test fires): lowest in New York (0.28), Colorado
  (0.31), and Washington (0.36); highest in Florida (1.41), Georgia (1.25), and Wyoming
  (1.02).
