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
