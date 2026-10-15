# AGENTS.md: Guide for AI agents working in this repo

You are an AI agent helping a human contributor in this repository. Read this file fully
before giving instructions or changing files. Its purpose is to let you (1) understand
what this repo is and how it flows, and (2) guide the user step by step.

---

## 1. What this repo is

A **class project**: a monorepo holding **multiple machine learning algorithms**, each
owned by a different person, plus shared utilities, shared datasets, and (later) a FastAPI
backend and React frontend.

**Audience and context you must respect**
- 4 contributors. Beginners at Python/ML and **especially at Git**. Assume little.
- Datasets come from Kaggle or open sources. Nothing is sensitive or private.
- Training is **local and CPU-only**. No GPU. Default ML library is **scikit-learn**
  (add others like PyTorch only if the user truly needs them).
- The design priority is: **simple, predictable, hard to mess up.** Prefer the boring,
  consistent option over the clever one.

**Fixed decisions (do not re-litigate or change unless the user asks)**

| Topic | Decision |
|---|---|
| Python | 3.12, managed with **pyenv** (`.python-version` = `3.12`) |
| Environment | **ONE `.venv` at the repo root.** No per-algorithm venvs, no per-algorithm requirements files |
| Dependencies | One root `requirements.txt` (runtime) and `requirements-dev.txt` (ruff, pytest, pre-commit) |
| Formatting/linting | **ruff**, run automatically on every commit via pre-commit |
| Datasets | **Shared** across all algorithms, stored in `data/`, never committed to Git |
| Saved models/metrics | Stored in `models/<algorithm_name>/`, never committed to Git |
| Tests | Optional for now |
| Experiment tracking | None. Each training run writes `metrics.json` |
| Code ownership | No CODEOWNERS. Convention: one person per algorithm folder |

**Not built yet (do not assume they exist)**: FastAPI backend (`backend/` is a
placeholder), React frontend (`frontend/` is a placeholder), Docker, CI/CD (GitHub
Actions). Whether models get served through the API is undecided, but every
`predict.py` is already shaped so a future API route can just import it.

---

## 2. Repo map

```
ml-platform/
├── AGENTS.md                  # this file
├── README.md                  # human setup + run instructions
├── CONTRIBUTING.md            # rules + beginner Git workflow
├── .python-version            # 3.12 (pyenv)
├── pyproject.toml             # ruff + pytest config
├── requirements.txt           # ALL runtime packages, one list
├── requirements-dev.txt       # dev tools (includes requirements.txt)
├── .pre-commit-config.yaml    # ruff on every commit
├── .gitignore
├── .env.example               # copy to .env; never commit .env
│
├── algorithms/
│   ├── _template/             # COPY THIS to start a new algorithm
│   │   ├── __init__.py
│   │   ├── model.py
│   │   ├── train.py
│   │   ├── predict.py
│   │   └── README.md
│   └── <algorithm_name>/      # one folder per algorithm (same 5 files)
│
├── shared/                    # code used by 2+ algorithms
│   ├── data_loader.py
│   ├── preprocessing.py
│   ├── evaluation.py
│   └── utils.py
│
├── data/                      # shared datasets (contents not in Git)
│   ├── README.md              # table of datasets: name, source, expected files
│   ├── raw/<dataset_name>/
│   └── processed/<dataset_name>/
│
├── models/<algorithm_name>/   # model.joblib + metrics.json (not in Git)
├── backend/                   # placeholder (FastAPI later)
├── frontend/                  # placeholder (React later)
├── tests/                     # optional
├── docs/
├── scripts/setup.sh           # Mac/Linux one-command setup (uses pyenv)
└── .github/pull_request_template.md
```

---

## 3. The flow (how everything connects)

```
data/raw/<dataset>/*.csv
        │  shared.data_loader.load_dataset("<dataset>")
        ▼
algorithms/<name>/train.py ──uses──► shared/preprocessing.py, shared/evaluation.py
        │  builds model via          shared/utils.py (save_model, save_metrics, seed)
        │  algorithms/<name>/model.py → build_model()
        ▼
models/<name>/model.joblib  +  models/<name>/metrics.json
        │  shared.utils.load_model("<name>")
        ▼
algorithms/<name>/predict.py → predict(input_data: dict)
        │  (future) imported by
        ▼
backend/ (FastAPI route)  ──►  frontend/ (React)
```

Key idea: **every algorithm follows the identical structure and contract**, so any
algorithm can be run, evaluated, and (later) served the same way.

### The contract (every algorithm must satisfy it)

| File | Must provide | Rules |
|---|---|---|
| `model.py` | `build_model()` returning an **untrained** estimator | Only defines the model. No data loading, no training |
| `train.py` | `main()` plus `if __name__ == "__main__": main()` | Loads data via `shared`, splits, trains, evaluates, saves model and `metrics.json` |
| `predict.py` | `predict(input_data: dict)` returning one prediction | Loads the saved model via `shared.utils.load_model`; caches it; no training here |
| `README.md` | Owner, what it does, data used, how to run, results | Keep it filled in |
| `__init__.py` | Empty file | **Never delete** (needed for imports) |

Template details worth knowing:
- `ALGORITHM_NAME = Path(__file__).resolve().parent.name`. It is derived from the folder
  name automatically. **Do not hardcode or rename it.**
- Imports inside an algorithm use `from .model import build_model` (relative) and
  `from shared.xxx import ...` (absolute). This is what makes copying `_template/` safe.
- In `train.py` the user sets `DATASET_NAME` (folder under `data/raw/`) and
  `TARGET_COLUMN`. It defaults to `evaluate_classification`; switch to
  `evaluate_regression` for regression.
- `predict()` takes a dict like `{"age": 30, "income": 50000}` and wraps it in a
  one-row DataFrame, so column names must match training.

### Shared utilities (what exists, so you reuse instead of rewriting)

| Module | Functions |
|---|---|
| `shared/data_loader.py` | `get_dataset_dir(name, processed=False)`, `load_dataset(name, filename=None, processed=False)` (loads a CSV; if no filename, the folder must contain exactly one CSV), `split_data(df, target_column, test_size=0.2, seed=42)` → `X_train, X_test, y_train, y_test` |
| `shared/preprocessing.py` | `fill_missing_values(df)`, `encode_categories(df)` (one-hot), `normalize(df)` |
| `shared/evaluation.py` | `accuracy`, `rmse`, `r2`, `evaluate_classification(y_true, y_pred)`, `evaluate_regression(y_true, y_pred)` (each returns a dict) |
| `shared/utils.py` | `get_project_root()`, `set_random_seed(seed=42)`, `get_model_dir(name)`, `save_model(model, name)`, `load_model(name)`, `save_metrics(dict, name)` |

**Rule for deciding where code goes:** if 2+ algorithms could use it → `shared/`. If it
only makes sense for one algorithm → keep it in that algorithm's folder. Prefer reusing
an existing shared function over writing a new one. Never hardcode file paths; use
`load_dataset` and the `utils` helpers.

---

## 4. Commands (always run from the repo root, with `.venv` activated)

```bash
# one-time setup (pyenv + venv): see README.md, or on Mac/Linux:  bash scripts/setup.sh
pyenv install 3.12 && pyenv local 3.12
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pre-commit install

# new algorithm
cp -r algorithms/_template algorithms/my_algorithm   # Windows: copy the folder in Explorer

# train / predict (dots, not slashes; no .py)
python -m algorithms.my_algorithm.train
python -m algorithms.my_algorithm.predict

# optional
pytest
ruff check . && ruff format .
```

Folder names: `lowercase_with_underscores` only (no spaces, dashes, or capitals).

---

## 5. Task playbooks (guide the user through these)

### A. First-time setup
1. Confirm pyenv is installed (`pyenv --version`). If not, point to the install links in `README.md`.
2. `pyenv install 3.12`, then in the repo `python --version` must show 3.12.x.
3. Create `.venv`, activate, `pip install -r requirements-dev.txt`, `pre-commit install`.
4. Verify: `pytest` passes.

### B. Create a new algorithm
1. Ask for a folder name (`lowercase_with_underscores`) and which dataset/problem type.
2. Make sure they're on their own Git branch (see section 6).
3. Copy `_template/` to `algorithms/<name>/`.
4. Edit `model.py` (`build_model()`), then `train.py` (`DATASET_NAME`, `TARGET_COLUMN`,
   classification vs regression), then `predict.py` (example input), then `README.md`.
5. Confirm the dataset exists in `data/raw/<dataset_name>/` (see C).
6. Run `python -m algorithms.<name>.train`; check `models/<name>/metrics.json` appears.
7. Run `python -m algorithms.<name>.predict` with a realistic example.
8. New packages? Add to `requirements.txt` (see D).

### C. Add or use a dataset
1. Download from the source (Kaggle/open data) into `data/raw/<dataset_name>/`.
2. Add a row to the table in `data/README.md` (name, source URL, expected files, who added it).
3. Load with `load_dataset("<dataset_name>")`. **Never commit data files.**
4. If cleaning is useful to several algorithms, put it in `shared/preprocessing.py`
   (tell the group, since this is shared code).

### D. Add a dependency
1. Confirm it's actually needed and not already covered by scikit-learn/pandas/numpy.
2. Add one line to the root `requirements.txt` and `pip install -r requirements.txt`.
3. Do it in its own small PR. Never create a per-algorithm requirements file or venv.

### E. Change shared code
1. Warn the user it affects everyone and needs a teammate's review.
2. Keep function names/signatures backward compatible. Other algorithms depend on them.
3. Make the change small and put it in its own PR.

### F. Prepare for the (future) API
No API exists yet. If asked, a FastAPI route should only import and call
`algorithms.<name>.predict.predict`. Don't restructure algorithms for it. Do not build
`backend/` or `frontend/` unless the user explicitly asks.

---

## 6. Git guidance for beginners

Assume the user knows little Git. Give exact copy-paste commands and explain each in one line.

```bash
git checkout main && git pull                         # get latest code
git checkout -b yourname/algorithm-name               # new branch (never work on main)
git add .
git commit -m "Short description of what changed"
git push -u origin yourname/algorithm-name
```
Then: open a Pull Request on GitHub, fill in the template, ask a teammate to review and
merge. GitHub Desktop is a fine alternative to the command line.

**Pre-commit behavior:** ruff runs on every commit. If it reformats files, the commit
stops. That is normal. Tell the user to run `git add .` and commit again.

**Never** have the user commit: anything in `data/raw/`, `data/processed/`, `models/`,
`.venv/`, or `.env`. (`.gitignore` blocks these; if `git status` shows them, stop and fix.)

---

## 7. Troubleshooting lookup

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: shared` / `algorithms` | Not at repo root, or ran `python file.py` | `cd` to repo root; use `python -m algorithms.<name>.train` |
| `python --version` isn't 3.12 | Outside repo, or pyenv not initialized in shell | `cd` into repo, `pyenv local 3.12`, open a new terminal |
| `ModuleNotFoundError: sklearn/pandas/...` | `.venv` not activated or packages not installed | Activate `.venv`; `pip install -r requirements-dev.txt` |
| `FileNotFoundError: Dataset folder not found` | Dataset not downloaded to `data/raw/<name>/` | Check `data/README.md`; download it there; check spelling of `DATASET_NAME` |
| `ValueError: Expected exactly one CSV` | Folder has 0 or 2+ CSVs | Pass `filename="file.csv"` to `load_dataset` |
| `FileNotFoundError: No saved model` | `predict` run before `train` | Run `python -m algorithms.<name>.train` first |
| `NotImplementedError: TODO: build...` | Template `model.py` not filled in | Implement `build_model()` |
| `KeyError` on target column | `TARGET_COLUMN` doesn't match dataset | Print `df.columns`; fix the constant |
| Prediction errors about columns | `predict` input keys differ from training columns | Match column names/preprocessing used in training |
| Commit "failed" and files changed | ruff auto-formatted | `git add .` then commit again |
| Data/model files appear in `git status` | `.gitignore` not matching | Don't commit; check path is under `data/raw|processed` or `models/` |

---

## 8. Behavior rules for you (the agent)

**Do**
- Work in small steps; confirm each succeeds before moving on.
- Ask the user where they are (setup? new algorithm? error?) before prescribing steps.
- Explain *why* in plain language; avoid jargon, define terms the first time.
- Use the existing structure, shared helpers, and naming conventions.
- Run/suggest commands from the repo root and mention activating `.venv`.
- Keep edits inside the user's own `algorithms/<name>/` folder unless they intend to change `shared/` or `requirements.txt`.

**Don't**
- Create extra virtual environments, per-algorithm requirements files, or `pyenv-virtualenv` envs.
- Edit other contributors' algorithm folders.
- Delete `__init__.py` files or rename the hardcoded contract functions (`build_model`, `main`, `predict`).
- Hardcode absolute or relative data paths; use `shared`.
- Commit or suggest committing data, models, `.venv`, or secrets.
- Add Docker, CI, an experiment tracker, GPU code, or the backend/frontend unprompted.
- Push to `main` directly or run destructive Git commands (`reset --hard`, force-push) without clear user confirmation and an explanation.

**Pre-PR checklist to walk the user through**
- [ ] Works from the repo root: `python -m algorithms.<name>.train` then `.predict`
- [ ] Algorithm `README.md` filled in (owner, data, how to run, results from `metrics.json`)
- [ ] Dataset documented in `data/README.md` if new
- [ ] New packages added to `requirements.txt` (own small PR)
- [ ] No data, models, or `.env` staged
- [ ] On a feature branch; PR template filled in