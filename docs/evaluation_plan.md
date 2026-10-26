# Plan: shared target and evaluation protocol

**Status:** planned, not built yet.

**Who builds what:** this plan covers only the shared pieces (data, split, features,
preprocessing, metrics, template, comparison script). Each member implements, tunes,
and documents their own model in `algorithms/<name>/`, including the baseline.

Every model in `algorithms/` predicts the same target, from the same features, on the
same split, scored with the same metrics. This is what makes the comparison fair (see
the CS 422 project requirements).

## Objective

When a wildfire is reported, predict how fast it will spread, using only what is known
at that moment: location, date, that day's weather, and the recent drought score.

The data only contains fires that happened, so it can't predict *whether* a fire will
start. This narrows "anticipating severity before it starts" from the proposal to
"severity at the moment of discovery". Explain this in the report.

## Target

`TARGET = log(1 + SPREAD_RATE)`, where `SPREAD_RATE` is acres burned per day until
containment (see `docs/wildfire_drought_merge_plan.md`).

- The log is used because spread rate is extremely skewed: the median is 0.1 acres/day
  and the max is about 65,000.
- About 62% of fires spread 0.25 acres/day or less, so a model that always predicts
  "small" will look good on average error. The metrics below check for this.
- Report predictions in acres/day too (`expm1(prediction)`) so they're readable.

## 1. Data

Change `scripts/process_wildfire_drought_data.py` to drop fires with no `SPREAD_RATE`
(no containment date) **before** sampling. The dataset then has 100,000 rows that all
have a target (currently only 85,896 do).

## 2. Split (fixed, saved, used by everyone)

Split by year:

| Split | Years | Approx. rows | Used for |
|---|---|---|---|
| Train | 2000–2014 | 69K | Fitting |
| Validation | 2015–2017 | 9K | Choosing hyperparameters |
| Test | 2018–2020 | 8K | Final score, once, after everything is frozen |

Why by year:
- It matches the use case: learn from past fires, predict future ones.
- 12,916 county-days have more than one fire, and those fires share identical weather.
  A random split would put some in train and some in test, which leaks.

The split is saved as a file listing each `FOD_ID` and its split, so the exact rows are
recorded and every model uses the same ones.

## 3. Features

Known at discovery time:

| Group | Columns |
|---|---|
| Location | `LATITUDE`, `LONGITUDE`, `STATE` |
| Timing | `DISCOVERY_DOY`, discovery hour (from `DISCOVERY_TIME`) |
| Weather on the discovery day | `PRECTOT`, `PS`, `QV2M`, `T2M`, `T2MDEW`, `T2MWET`, `T2M_MAX`, `T2M_MIN`, `T2M_RANGE`, `TS`, `WS10M`, `WS10M_MAX`, `WS10M_MIN`, `WS10M_RANGE`, `WS50M`, `WS50M_MAX`, `WS50M_MIN`, `WS50M_RANGE` |
| Drought | `SCORE` |

Not allowed as features:

| Columns | Why |
|---|---|
| `FIRE_SIZE`, `FIRE_SIZE_CLASS`, `CONT_DATE`, `CONT_DOY`, `CONT_TIME`, `DURATION_DAYS`, `SPREAD_RATE` | Only known after the fire, or part of the target (leakage) |
| `FOD_ID`, `FIRE_NAME`, `COUNTY`, `FIPS_CODE`, `FIPS_NAME`, `DROUGHT_FIPS` | IDs or names, not useful signal |
| `NWCG_CAUSE_CLASSIFICATION`, `NWCG_GENERAL_CAUSE`, `NWCG_CAUSE_AGE_CATEGORY` | The same for every row (all natural fires) |
| `MATCH_METHOD`, `MATCH_DISTANCE_KM`, `SCORE_DATE` | Made by the merge, not facts about the fire |
| `FIRE_YEAR`, `DISCOVERY_DATE` | With a split by year, the test years are never seen in training |

## 4. Preprocessing (no leakage)

A shared scikit-learn pipeline every model wraps around its estimator:
- Numbers: fill missing values with the median (3,432 rows have no `DISCOVERY_TIME`),
  then scale.
- `STATE`: one-hot encoding.

It is fitted on training data only and then applied to validation and test data. The
existing functions in `shared/preprocessing.py` compute their statistics on the whole
dataset, so they must not be used for these models.

Model-specific preprocessing is allowed when the model's README explains why.

## 5. Metrics

| Metric | Role |
|---|---|
| MAE on the log scale | **Primary** |
| RMSE on the log scale | Supporting |
| R² | Supporting |
| MAE on the top 10% fastest-spreading test fires | Supporting: catches models that only predict "small" |

## 6. Baseline

`algorithms/baseline/`: always predicts the training median (the best constant for MAE).
Every other model is compared against it. A team member builds it like any other model,
from the template.

## 7. Training workflow (template `train.py`)

1. Load the shared features, target, and split.
2. For each setting in the model's `PARAM_GRID`: fit on train, score MAE on validation.
3. Pick the best setting and freeze it.
4. Refit on train + validation with the frozen setting and score the test set once.
5. Repeat with 5 seeds (`0, 1, 2, 3, 4`). For a model with no randomness, one run is
   enough; say so in its README.

`models/<name>/metrics.json` records the search space, the chosen setting, validation
and test scores for each seed, and package versions.

## 8. Comparison

`scripts/compare_models.py` reads every model's `metrics.json` and writes
`results/comparison.csv`:
- One row per model: model, responsible member, validation and test results labeled
  separately, mean ± standard deviation across seeds.
- Includes the baseline.
- `results/` is committed (the submission needs the result tables), unlike `models/`.

## 9. Reproducibility

- Pin exact package versions in `requirements-lock.txt`.
- Tests: the split has no overlap and gives the same rows every time; preprocessing is
  never fitted on validation or test rows.
- Later: a script that copies the code to `.py.txt` files for the course submission.
