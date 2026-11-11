# K-Nearest Neighbors (median KNN)

**Owner:** Vincent Chen

## What it does
Predicts how fast a newly reported wildfire will spread (`log(1 + acres per day)`) from
the fires most similar to it in the training data. `SPREAD_RATE = FIRE_SIZE /
DURATION_DAYS` is average final acres divided by days to containment, not an
instantaneous spread rate. This is regression, not the earlier Low/Medium/High
classification experiments.

The model is a custom `MedianKNNRegressor` (in `model.py`): it finds the nearest
training fires with scikit-learn's neighbor search and predicts the **median** of their
targets, either unweighted (`uniform`) or weighted by inverse distance (`distance`). The
team chose the median because the target is skewed (`docs/discussion_log.md`, entry 15).
It is the team's non-parametric, local model: it needs no assumption about the shape of
the relationship, and shows how far "similar fires" alone can go.

## Data
Uses the shared experiment (`docs/evaluation_plan.md`): target `log(1 + SPREAD_RATE)`,
the 42 features in `shared/experiment.py`, and the committed `train.csv.gz` (79,961
rows), `validation.csv.gz` (10,026), and `test.csv.gz` (10,013) in
`data/processed/wildfire_drought/`.
- Model-specific preprocessing: none. Only the shared pipeline (`build_preprocessor()`):
  median fill and scaling for the numeric features, one-hot encoding for the five
  categorical features (`STATE`, `Land_Cover`, `OWNER_DESCR`, `NWCG_REPORTING_AGENCY`,
  `Ecoregion_NA_L2CODE`). Scaling matters for KNN because distances would otherwise be
  dominated by large-valued columns. It is fitted on the training rows only (on train +
  validation for the final model).

## Settings
Library: scikit-learn `NearestNeighbors`; the median is computed in `model.py`.
Every setting was chosen by validation MAE only.

| Setting | Values tried | Best |
|---|---|---|
| `n_neighbors` | 5, 15, 31 | **31** |
| `weights` | `uniform`, `distance` | **`distance`** |

Validation MAE for all 6 combinations: 5 neighbors 0.613 / 0.6125 (uniform / distance),
15 neighbors 0.5785 / 0.5775, 31 neighbors 0.5774 / 0.5767.
- **Final setting:** `n_neighbors=31`, `weights="distance"`.
- **Search limit:** the best `n_neighbors` is the largest value tried, so a larger value
  might do a little better. Differences between the top three settings are about 0.001.
- **Defaults not tuned:** `algorithm="auto"` (neighbor search method), distance metric
  (Euclidean).
- **Seeds:** one run (`SEEDS = [0]`). KNN has no randomness for a fixed dataset and
  setting, so the standard deviation of 0 in the table means "not applicable", not "no
  variability".

## How to run (from the repo root)
```bash
python -m algorithms.knn.train
python -m algorithms.knn.predict
python -m scripts.compare_models
```
Training is fast (about 0.3 seconds per fit). Results are saved to
`models/knn/metrics.json` and copied to `results/metrics/knn.json` by `compare_models`;
the trained model (`model.joblib`) is not committed.

## Results
One run. MAE and RMSE are on the log scale.

| Split | MAE (primary) | RMSE | R² | MAE, fastest 10% |
|---|---|---|---|---|
| Validation | 0.5767 | 1.2780 | 0.107 | 3.315 |
| Test | 0.6058 | 1.3074 | 0.104 | 3.403 |

Vincent's earlier mean-based KNN had validation MAE 0.6729 (recorded before this
README was revised), so switching to the median lowered it by about 14%. Aiming at the
median usually costs R² and fast-fire accuracy, the trade-off recorded in discussion log
entry 15.

## Notes
- **Versus the baseline** (training median; test MAE 0.711): 14.7% lower. It is behind
  LightGBM (0.565) and random forest (0.579) and ahead of Huber regression (0.622).
- **Fast fires:** MAE on the fastest 10% is 3.403 on test, about 5.6 times the overall
  MAE and not much better than the baseline's 4.257. This would be a material
  limitation for emergency response.
- **Split:** the team uses a grouped county-day random split, not a future-year holdout,
  so the results do not show how the model would do on future years.
- **Prediction-time information:** the weather features describe the discovery day, and
  some daily values might not have been known at the moment of reporting. The team
  should review this.
- **Attribution:** this KNN package was initially written with AI assistance (ChatGPT)
  and needs Vincent's own check of the code, metrics, and interpretation. Include it in
  the team's generative-AI disclosure.

## Error analysis
Test set (10,013 fires), from `python -m scripts.error_analysis` (full tables in
`results/error_analysis.csv` and `results/error_analysis_summary.csv`). The model is the
final one, refit on train + validation. A fast fire spreads at least 11 acres/day (10.7%
of test fires). The group labels (lifetime, size class) are only used to slice the
errors; they are not features.

- **Fast fires are missed.** The 10% fastest fires have an actual median of 52.35
  acres/day; the median prediction is 1.0, and 99.1% are underpredicted. Taking the
  median of 31 neighbors pulls every prediction toward the typical small fire. As a
  ranking it is the weakest of the learned models on ROC-AUC (0.765), about level with
  Huber on PR-AUC (0.312 vs 0.306; 0.107 by chance). Flagging the 20% of fires with the
  highest predictions catches 54% of fast fires with precision 0.29.
- **By fire size class** (test MAE, baseline in brackets): A 0.104 (0.030), B 0.489
  (0.635), C 1.842 (2.552), D 3.107, E 3.694, F 4.777, G 6.172 (6.781).
- **By fire lifetime** (test MAE): 1–2 days 0.485 (0.590), 3–30 days 1.003 (1.116), 31–90
  days 1.351 (1.375), 91+ days 1.993 (1.980). It beats the baseline up to a month, and
  is no better for the longest fires (38 test fires).
- **By state** (states with 200+ test fires): lowest in New York (0.25), Colorado (0.30),
  and Oregon (0.39); highest in Florida (1.08), Georgia (1.00), and Nevada (0.95).
- **Likely reason (not tested):** the best `n_neighbors` is the largest value tried, so
  larger neighborhoods help typical fires but smooth over the rare fast ones.
