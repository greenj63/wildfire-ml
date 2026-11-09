# Huber Regression

**Owner:** Jack Greene

## What it does

One or two sentences: which algorithm, and why it's worth comparing against the others.
Predicts how fast a wildfire spreads (log(1 + SPREAD_RATE)) using a specialized form of
Linear Regression: Huber Regression.

Huber Regression minimizes different objectives depending on the size of the error,
MSE for small errors, MAE to penalize large errors. This is essential for datasets
such as the wildfire dataset which have extreme outliers.

## Data

Uses the shared experiment (`docs/evaluation_plan.md`): target `log(1 + SPREAD_RATE)`,
the 42 features in `shared/experiment.py`, and the committed `train.csv.gz` (79,961
rows), `validation.csv.gz` (10,026), and `test.csv.gz` (10,013) in
`data/processed/wildfire_drought/`. The features cover location, timing, the drought
score, terrain, vegetation, weather and fire-danger indices at the ignition point, land
owner, reporting agency, nearby fire stations, ecoregion, and population (most from FPA
FOD-Attributes, Pourmohamad et al., 2024).

- Model-specific preprocessing: none. Only the shared pipeline (median fill, scaling,
  one-hot categories).

## Settings

- `PARAM_GRID` (search space) and why these values:

**Parameters**
PARAM_GRID = {
"epsilon": [1.0, 1.1, 1.15, 1.25, 1.35],
"alpha": [1e-6, 1e-4, 1e-2, 1],
}

The epsilon values indicate where the loss function switches from MSE to MAE.
This means that smaller errors (often fires with SPREAD_RATE = ~ 0.1)
are less influenced by larger residuals. These smaller values were used
to fine tune the specific point where errors are minimized (~1.1)

The alpha values seek to minimize coefficients to prevent overfitting.
Seeing as the dataset is large (100K rows, 42 features), smaller values should
be favored. Thus, the parameters skew towards 0.

**Chosen Setting**
alpha = 0.0001
epsilon = 1.1

**Defaults**
-- max_params = 500 (Little difference at higher values, faster training)

- Chosen setting (`best_params` in `metrics.json`):

**Randomness**
Huber Regression is a deterministic model and thus has no randomness (seed = 0)

## How to run (from the repo root)

```bash
python -m algorithms.huber-regression.train
python -m algorithms.huber-regression.predict
```

Then update the team table: `python -m scripts.compare_models`

## Results

One run (seed 0). Huber regression has no randomness, so there is no spread across seeds and std is not applicable. MAE is on the log(1 + SPREAD_RATE) scale. Best setting: `epsilon` 1.1, `alpha` 0.0001. Fit time: 14.3 s.

| Split      | MAE   | RMSE  | R²    | MAE (top 10%) |
| ---------- | ----- | ----- | ----- | ------------- |
| Validation | 0.591 | 1.284 | 0.098 | 3.369         |
| Test       | 0.622 | 1.325 | 0.080 | 3.502         |

Source: `results/comparison.csv` (huber-regression row) and `models/huber-regression/metrics.json`.

## Notes

- **The settings barely matter.** Validation MAE across all 20 combinations ranges from 0.5905 to 0.5954. The best setting beats the next-best by about 0.00006. Within a fixed `alpha`, MAE rises as `epsilon` moves above 1.1, and `alpha` has almost no effect. Treat `epsilon` 1.1 as a reasonable choice, not a clear winner.
- **Versus the baseline:** validation MAE 0.591 (baseline 0.681) and test MAE 0.622 (baseline 0.711), both on the log scale.
- **Low R²:** about 0.08 to 0.10 on the log scale. The model explains only a small share of the variance, so the gain over the baseline is real but the predictions are coarse.
- **Top-10% MAE is about 5.5 times the overall MAE.** Check how `mae_top10` is defined in `shared/` before drawing conclusions from it.
- **Protocol:** tuned on validation; the test score comes from a model refit on train + validation, as recorded in `comparison.csv`.
- **Not yet checked:** how often predictions are negative on the log scale (see the clipping note in the Huber discussion), and `predict.py`, whose example input is missing most raw columns and will fail until it is rebuilt.
