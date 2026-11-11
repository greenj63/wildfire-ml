# Plan: shared target and evaluation protocol

**Status:** shared pieces built (`shared/experiment.py`, `build_preprocessor()`,
`evaluate_spread_rate()`, the `train.csv.gz`/`validation.csv.gz`/`test.csv.gz` files, the template, `scripts/compare_models.py`).
The baseline and four models are built and trained on the 42-feature dataset
(`results/comparison.csv`).

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

One script (`python -m scripts.make_split`) splits the 100,000 fires at random with a
fixed seed (42), using scikit-learn's `GroupShuffleSplit`:

| Split | Rows | Used for |
|---|---|---|
| Train | 79,961 (80%) | Fitting |
| Validation | 10,026 (10%) | Choosing hyperparameters |
| Test | 10,013 (10%) | Final score, once, after everything is frozen |

Why grouped:
- 12,916 county-days have more than one fire, and those fires share identical weather
  and drought values. A plain `train_test_split` would put some in train and some in
  test, which leaks. Grouping by county + discovery date keeps each county-day in one
  file.

The three splits are saved as `train.csv.gz`, `validation.csv.gz`, and `test.csv.gz` in
`data/processed/wildfire_drought/` (gzip-compressed) and committed to Git, so every member pulls the exact
same rows (each row keeps its `FOD_ID`). The same seed and data always give the same
files.

## 3. Features

Known at discovery time (42 features; the full list is in `shared/experiment.py`). Most
come from FPA FOD-Attributes (Pourmohamad et al., 2024), joined by `FOD_ID`; column
meanings are in that paper's Table S1.

| Group | Columns |
|---|---|
| Location | `LATITUDE`, `LONGITUDE`, `STATE` |
| Timing | `DISCOVERY_DOY`, discovery hour (from `DISCOVERY_TIME`) |
| Drought | `SCORE` (weekly county score) |
| Terrain | `Elevation`, `Slope`, `TPI`, `TRI`, aspect (from `Aspect`, as sine/cosine plus a flat-ground flag) |
| Vegetation | `Land_Cover` (category), `NDVI-1day` |
| Weather at the ignition point on the discovery day (gridMET) | `pr`, `tmmn`, `tmmx`, `rmin`, `rmax`, `sph`, `vs`, `srad`, `vpd`, `erc`, `bi`, `fm100`, `fm1000`, wind direction (from `th`, as sine/cosine) |
| How unusual the day was | `sph`, `vs`, `fm100`, `bi`, `vpd`, `erc` percentiles (text ranges like `"30-50%"`, turned into their midpoints) |
| Response and people | `OWNER_DESCR`, `NWCG_REPORTING_AGENCY` (categories), fire stations within 10 and 20 km (empty = 0), `Population` |
| Region | `Ecoregion_NA_L2CODE` (category) |

The conversions happen in `add_derived_columns()`, which `predict()` also uses.

The county weather columns (`PRECTOT`, `T2M`, `WS10M`, ...) are still in the files but
not used as features: once the point weather was added, they made no difference on
validation (see `docs/discussion_log.md`).

Not allowed as features:

| Columns | Why |
|---|---|
| `FIRE_SIZE`, `FIRE_SIZE_CLASS`, `CONT_DATE`, `CONT_DOY`, `CONT_TIME`, `DURATION_DAYS`, `SPREAD_RATE` | Only known after the fire, or part of the target (leakage) |
| `FOD_ID`, `FIRE_NAME`, `COUNTY`, `FIPS_CODE`, `FIPS_NAME`, `DROUGHT_FIPS` | IDs or names, not useful signal |
| `NWCG_CAUSE_CLASSIFICATION`, `NWCG_GENERAL_CAUSE`, `NWCG_CAUSE_AGE_CATEGORY` | The same for every row (all natural fires) |
| `MATCH_METHOD`, `MATCH_DISTANCE_KM`, `SCORE_DATE` | Made by the merge, not facts about the fire |
| `FIRE_YEAR`, `DISCOVERY_DATE` | The use case is future fires, whose year never appears in the training data |
| FPA FOD-Attributes: `MTBS_*`, `ICS_209_PLUS_*` | Only exist for large fires (96% of class G vs 0% of class A have an MTBS ID), so they reveal the fire's size |
| FPA FOD-Attributes: `*_5D_mean`, `*_5D_min`, `*_5D_max` | Averaged over 5 days centered on ignition, so they include days after discovery |
| FPA FOD-Attributes: `tmmn_Percentile`, `tmmx_Percentile` | `">90%"` for every fire, so they carry no information |

## 4. Preprocessing (no leakage)

A shared scikit-learn pipeline every model wraps around its estimator:
- Numbers: fill missing values with the median (3,432 rows have no `DISCOVERY_TIME`),
  then scale.
- Categories (`STATE`, `Land_Cover`, `OWNER_DESCR`, `NWCG_REPORTING_AGENCY`,
  `Ecoregion_NA_L2CODE`): one-hot encoding.

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
Every other model is compared against it. It was built like any other model, from the
template (owner: Arlim Macaldo). It has no randomness, so it runs once (`SEEDS = [0]`).

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
`results/comparison.csv`. It uses `models/<name>/metrics.json` when it exists on your
computer, and the committed copy in `results/metrics/<name>.json` for every other model,
so a teammate's committed results are never dropped from the table:
- One row per model: model, responsible member, validation and test results labeled
  separately, mean ± standard deviation across seeds.
- Includes the baseline.
- `results/` is committed (the submission needs the result tables), unlike `models/`.

## 9. Reproducibility

- Pin exact package versions in `requirements-lock.txt`.
- Tests: the split has no overlap and gives the same rows every time; preprocessing is
  never fitted on validation or test rows.
- Later: a script that copies the code to `.py.txt` files for the course submission.
