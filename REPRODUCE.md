# Reproducing the main comparison

This explains how to reproduce `results/comparison.csv`: five models predicting how fast a
newly reported wildfire spreads (`log(1 + acres per day)`), scored on the same fires. The
shared protocol (target, features, split, metrics) is in `docs/evaluation_plan.md`; each
model's settings and results are in `algorithms/<name>/README.md`.

| Model | Folder | Owner |
|---|---|---|
| Baseline (training median) | `algorithms/baseline` | Arlim Macaldo |
| LightGBM | `algorithms/light_gbm` | Arlim Macaldo |
| Random forest | `algorithms/random_forest` | Erick Sanchez |
| Median KNN | `algorithms/knn` | Vincent Chen |
| Huber regression | `algorithms/huber-regression` | Jack Greene |

## 1. Requirements
- Python 3.12 (`.python-version`), CPU only, no GPU. Most results were recorded with
  Python 3.12.14; the random forest run used 3.12.10.
- Exact package versions are pinned in `requirements-lock.txt`. The ones that matter:

| Package | Version |
|---|---|
| numpy | 2.5.4 |
| pandas | 3.0.6 (the random forest run used 3.1.1) |
| scikit-learn | 1.9.1 |
| lightgbm | 4.7.0 |
| scipy | 1.18.1 |
| joblib | 1.6.0 |

Each model's `results/metrics/<name>.json` records the versions it was run with.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-lock.txt
python -m pytest -q                  # all tests should pass
```
Run every command from the repo root, with the environment active. See `README.md` for
the pyenv setup.

## 2. Data
Nothing to download. The shared split is committed in `data/processed/wildfire_drought/`:
`train.csv.gz` (79,961 fires), `validation.csv.gz` (10,026), and `test.csv.gz` (10,013).
Each row keeps its `FOD_ID`. The same fires and the same split are used by every model.

- **Split:** random ~80/10/10, with each county-day kept in one file (scikit-learn
  `GroupShuffleSplit`, seed 42), so fires that share identical weather never straddle
  train and test.
- **Rebuilding the data (optional).** The split files come from four public sources,
  listed with download links in `data/README.md`: the FPA FOD wildfire database
  (Kaggle), the US drought and meteorological dataset (Kaggle), the Census 2020 county
  Gazetteer, and FPA FOD-Attributes (Pourmohamad et al., 2024, Zenodo, 4.7 GB). Put
  each raw file where `data/README.md` says, then:
  ```bash
  python -m scripts.process_wildfire_data
  python -m scripts.process_drought_data
  python -m scripts.process_wildfire_drought_data   # samples 100,000 fires, seed 42
  python -m scripts.make_split                      # writes train/validation/test
  ```
  Rebuilding is only needed to change how the data is made, and then every model must be
  retrained. The drought dataset's licence for sharing derived data is still an open
  item (`docs/discussion_log.md`).

## 3. Seeds and protocol
- **Split seed:** 42. **Data sampling seed:** 42.
- **Model seeds:** `0, 1, 2, 3, 4` for LightGBM and random forest (5 runs, mean ± std).
  The baseline, Huber regression, and KNN have no randomness, so they run once
  (`SEEDS = [0]`); their std of 0 or blank means "not applicable".
- **Tuning:** each model's `PARAM_GRID` (in its `model.py`) is searched on the validation
  set, with seed 0. The best setting is then frozen.
- **Scoring:** for each seed, a validation score (model fit on train) and a test score
  (model refit on train + validation with the frozen setting, scored once on test).
  Validation and test are reported separately.
- **Leakage:** all learned preprocessing (median fill, scaling, one-hot) sits inside the
  model pipeline, so it is fitted on training rows only.
- **Primary metric:** MAE on the log scale. Supporting: RMSE, R², and MAE on the 10%
  fastest-spreading fires. Fit time is recorded as well.

## 4. Commands
```bash
python -m algorithms.baseline.train
python -m algorithms.huber-regression.train
python -m algorithms.knn.train
python -m algorithms.light_gbm.train
python -m algorithms.random_forest.train
python -m scripts.compare_models          # results/comparison.csv
python -m scripts.error_analysis          # results/error_analysis*.csv
```
Each `train` writes `models/<name>/model.joblib` and `models/<name>/metrics.json` (not
committed). `compare_models` copies each model's metrics to `results/metrics/<name>.json`
and builds the table. Run time on a laptop CPU (estimates; the random forest dominates):

| Step | Time |
|---|---|
| baseline, KNN | seconds |
| Huber regression | about 2 minutes (20 settings, about 4 s per fit) |
| LightGBM | about 3 minutes (26 fits at about 7 s) |
| random forest | an hour or more (108 settings, then 10 final fits at about 2.5 minutes each) |
| `compare_models`, `error_analysis` | under 30 seconds |

**Shortcut:** `python -m scripts.compare_models` alone rebuilds the table from the
committed `results/metrics/*.json`, with no retraining. `error_analysis` needs the
trained models, so run the `train` commands first.

## 5. Expected results
Test split. MAE and RMSE are on the log scale. The values are mean ± std over the runs
listed (from `results/comparison.csv`).

| Model | Runs | Test MAE (primary) | Test RMSE | Test R² | MAE, fastest 10% |
|---|---|---|---|---|---|
| LightGBM | 5 | 0.5648 ± 0.0008 | 1.1749 | 0.277 | 2.947 |
| Random forest | 5 | 0.5793 ± 0.0005 | 1.1983 | 0.247 | 2.948 |
| KNN (median) | 1 | 0.6058 | 1.3074 | 0.104 | 3.403 |
| Huber regression | 1 | 0.6215 | 1.3248 | 0.080 | 3.502 |
| Baseline (median) | 1 | 0.7106 | 1.5410 | −0.245 | 4.257 |

Retraining should give nearly the same numbers for the deterministic models (baseline,
Huber, KNN); the last digit can differ between machines (Huber's test MAE came out as
0.6216 on one run and 0.6215 on another). LightGBM and random forest vary by seed, so
compare against the mean ± std above. When the random forest's saved final setting was
refit once (seed 0), it gave test MAE 0.5797 against the saved 0.5786, about twice its
seed-to-seed spread; different package versions or machines may account for that. The
LightGBM and baseline retraining times and results in the table were not re-run when
this file was written; they come from the committed `results/metrics/*.json`.

## 6. Saved configurations and results
- `results/comparison.csv`: one row per model with validation and test metrics, runs,
  chosen settings, and protocol.
- `results/metrics/<name>.json`: the search space, every setting tried with its
  validation MAE, the chosen setting, each seed's scores, fit times, and package versions.
- `results/error_analysis_summary.csv` and `results/error_analysis.csv`: fast-fire
  detection, underprediction, and test MAE by fire lifetime, size class, and state, for
  every model (test set, final models).
- `docs/discussion_log.md`: the team's decisions and the evidence behind them.

## 7. Limitations of the evaluation
- **One split.** Results come from a single fixed random split, not cross-validation.
  The standard deviations measure seed variation only, not variation from a different
  split. The split is random, so it does not measure forecasting accuracy for future
  years.
- **Weather at the discovery day.** Some daily values might not have been known at the
  moment a fire was reported.
- **Single-run models.** Baseline, Huber, and KNN ran once because they are
  deterministic.

## 8. Course submission format
The course asks for Python scripts uploaded as `.py.txt` files, with the report and slides.
A script that copies the code to `.py.txt` files has not been written yet; until then,
rename each `.py` file to `.py.txt` when uploading and restore `.py` to run it.
