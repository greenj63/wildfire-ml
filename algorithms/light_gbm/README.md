# <Algorithm name>

**Owner:** your name

## What it does
One or two sentences: which algorithm, and why it's worth comparing against the others.

## Data
Uses the shared experiment (`docs/evaluation_plan.md`): target `log(1 + SPREAD_RATE)`,
features from `shared/experiment.py`, and the committed `train.csv`, `validation.csv`, `test.csv` in
`data/processed/wildfire_drought/`.
- Model-specific preprocessing (if any) and why:

## Settings
- `PARAM_GRID` (search space) and why these values:
- Chosen setting (`best_params` in `metrics.json`):
- Defaults you didn't tune:
- Seeds: `0-4`, or one run if the model has no randomness (say so here).

## How to run (from the repo root)
```bash
python -m algorithms.<folder_name>.train
python -m algorithms.<folder_name>.predict
```
Then update the team table: `python -m scripts.compare_models`

## Results
Paste the validation and test rows for this model from `results/comparison.csv`
(mean ± std across seeds; MAE is on the log scale).

## Notes
Anything a teammate should know (assumptions, known problems, failure cases, ideas).
