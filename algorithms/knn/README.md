# K-Nearest Neighbors (KNN) — Wildfire Spread-Rate Regression

**Owner:** Replace `MEMBER` in `model.py` with the contributor's name.

## Objective

Predict the team-defined target `LOG_SPREAD_RATE = log(1 + SPREAD_RATE)`, where
`SPREAD_RATE = FIRE_SIZE / DURATION_DAYS` in acres/day. Unlike the earlier
individual KNN experiments, this is **regression**, not Low/Medium/High
classification, and uses exactly the team’s saved split files.

## Dataset and features

Uses the committed `data/processed/wildfire_drought/{train,validation,test}.csv`
from the shared repository. `shared/experiment.py` defines the features and
outcome. `shared/preprocessing.py` median-imputes and standardizes numeric
features and one-hot encodes `STATE`. These learned transformations are fit on
the training split only (and on train+validation when fitting the final model).

## Model choice and experiment

- Scikit-learn `KNeighborsRegressor`.
- Hyperparameters tuned with shared **validation MAE on log scale**:
  `n_neighbors` in `[5, 15, 31]`; `weights` in `[uniform, distance]`.
- Shared `train.py` selects one setting on validation, then refits on training
  plus validation and evaluates once on the team's unchanged held-out test set.
- Primary metric: MAE on log scale. Supporting: RMSE, R², and MAE for the top
  10% fastest-spreading fires. `shared/evaluation.py` implements these.
- KNN is deterministic for a fixed dataset and hyperparameter choice, so a
  single seed (`0`) is used. There is no run-to-run stochastic variability.
- Nearest-neighbor search can be computationally costly for the full training
  set. Keep the training data and shared test rows unchanged for comparisons;
  document any future compute-driven modification.

## Commands (from **repository root**)

```bash
python -m algorithms.knn.train
python -m algorithms.knn.predict
python -m scripts.compare_models
```

After training, results are saved in `models/knn/metrics.json` and the pipeline
is saved as `models/knn/model.joblib`. The team comparison table is generated at
`results/comparison.csv`; the team should commit the result table/metrics copies
following its repository instructions (do not commit the trained model).

## Interpretation and limitations

- High prediction error for rapidly spreading fires would be a material
  limitation for emergency-response use; examine `mae_top10` explicitly.
- `SPREAD_RATE` is *average final acres divided by duration to containment*;
  it is not a physical instantaneous spread rate.
- The team uses a grouped county-day **random split**, not a future-year
  holdout. The results therefore do not establish prospective forecasting
  performance across time.
- The team's weather features summarize the discovery **day**; some daily
  aggregates might not have been available at the actual reporting time.
  This potential prediction-time leakage should be reviewed with the group.

## Reproducibility and attribution

Record the version details saved by the training script. The dataset's public
source links and merge method are documented in `data/README.md` and
`docs/wildfire_drought_merge_plan.md`. This KNN package was initially
AI-assisted (ChatGPT) and requires independent verification by its contributor;
include its use in the team's generative-AI disclosure and confirm the code,
metrics, and interpretation yourself.

**Results:** Not reported here because this KNN version has not yet been run
on the complete shared split files. Do not reuse accuracy/F1 scores from
previous fire-size classification experiments as regression results.
