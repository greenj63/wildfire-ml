# Random Forest Regression

**Owner:** Erick Sanchez

## What it does
Implements a Random Forest Regressor ensemble to predict wildfire spread rates. It captures complex, non-linear relationships between drought indices and fire behavior, while utilizing hyperparameter constraints to actively prevent overfitting.

## Data
Uses the shared experiment (`docs/evaluation_plan.md`): target `log(1 + SPREAD_RATE)`,
features from `shared/experiment.py`, and the committed `train.csv`, `validation.csv`, `test.csv` in
`data/processed/wildfire_drought/`.
- Model-specific preprocessing (if any) and why: None. The algorithm relies entirely on the shared preprocessor to fill data gaps and scale features before fitting[cite: 1, 3].

## Settings
- `PARAM_GRID` (search space) and why these values: `max_depth`, `min_samples_leaf`, and `min_samples_split` are constrained to prevent individual decision trees from memorizing the training data, directly combating the model's tendency to overfit. 
- Chosen setting (`best_params` in `metrics.json`): [Update after running train.py]
- Defaults you didn't tune: Bootstrap sampling is left as True, and criterion is squared error.
- Seeds: `0-4`.

## How to run (from the repo root)
```bash
python -m algorithms.random_forest.train
python -m algorithms.random_forest.predict