# ML Platform

A class project: several machine learning algorithms (one per contributor) in one
repo, sharing datasets and utility code. A FastAPI backend and React frontend will
be added later.

## Folder map

| Folder | What it is |
|---|---|
| `algorithms/` | One folder per algorithm. Copy `_template/` to start yours. |
| `shared/` | Code used by 2+ algorithms (loading data, metrics, helpers). |
| `data/` | Shared datasets (downloaded by you, NOT in Git), except the team's `train.csv`, `validation.csv`, and `test.csv` in `data/processed/wildfire_drought/`, which are committed. See `data/README.md`. |
| `models/` | Saved trained models + `metrics.json` (NOT in Git). |
| `backend/` | FastAPI app (placeholder for now). |
| `frontend/` | React app (placeholder for now). |
| `tests/` | Optional tests. |
| `docs/` | Longer notes and diagrams. |

## One-time setup (pyenv + Python 3.12)

We use **pyenv** to manage the Python version. The file `.python-version` in the repo
root tells pyenv to use 3.12 automatically whenever you are inside this folder.
Run everything below from the repo root (the folder containing this README).

**Step 0: install pyenv (once per computer)**
- Mac / Linux: https://github.com/pyenv/pyenv#installation
- Windows: install **pyenv-win**: https://github.com/pyenv-win/pyenv-win#installation

**Step 1: install Python 3.12 through pyenv (once per computer)**
```bash
pyenv install 3.12      # installs the latest 3.12.x (skip if already installed)
pyenv local 3.12        # only needed if .python-version is missing
python --version        # should print Python 3.12.x
```
If `python --version` does not say 3.12, pyenv isn't set up correctly. Check the
pyenv install instructions for your shell, then open a new terminal.

**Step 2: create the single repo environment and install packages**

*Mac / Linux*
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pre-commit install
```

*Windows (PowerShell)*
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
pre-commit install
```

(Mac/Linux shortcut: `bash scripts/setup.sh` does Step 2 for you.)

pyenv picks the Python version; `.venv` holds the packages. There is ONE `.venv` for
the whole repo. Do not create another one inside an algorithm folder, and do not use
`pyenv-virtualenv` or per-algorithm environments. Each time you open a new terminal,
activate it again.

## Running an algorithm (always from the repo root)

```bash
python -m algorithms.<algorithm_name>.train      # train and save the model
python -m algorithms.<algorithm_name>.predict    # try a prediction
```

Use dots, not slashes, and no `.py`.

After training, rebuild the team comparison table (`results/comparison.csv`):
```bash
python -m scripts.compare_models
```
The target, features, split, and metrics every model shares are described in
`docs/evaluation_plan.md`. Data setup is in `data/README.md`.

## Adding a new algorithm

```bash
cp -r algorithms/_template algorithms/my_algorithm      # Windows: copy the folder in File Explorer
```
Then edit the 4 files inside (see the comments marked `TODO`). Use
`lowercase_with_underscores` for the folder name.

## Troubleshooting

- **`ModuleNotFoundError: shared` or `algorithms`**: you are not at the repo root,
  or you ran `python file.py` instead of `python -m ...`.
- **`command not found: python -m ...`**: activate the environment first.
- **Wrong Python version** (`python --version` isn't 3.12): you're probably outside the repo folder, or pyenv isn't set up in your shell. `cd` into the repo and run `pyenv local 3.12`.
- **Commit failed and files changed**: that's ruff formatting your code. Run
  `git add .` and commit again.





## File Structure of the repo
```
ml-platform/
├── README.md                    # Setup + how to run (start here)
├── CONTRIBUTING.md              # Beginner Git guide + 5 rules
├── .python-version              # Contains: 3.12
├── pyproject.toml               # Ruff settings (formatting/linting rules)
├── requirements.txt             # Everyone's packages, one list
├── requirements-dev.txt         # ruff, pytest, pre-commit
├── .pre-commit-config.yaml      # Optional auto-format on commit
├── .gitignore
├── .env.example
│
├── algorithms/
│   ├── __init__.py
│   ├── _template/               # Copy this to start a new algorithm
│   │   ├── __init__.py
│   │   ├── model.py
│   │   ├── train.py
│   │   ├── predict.py
│   │   └── README.md
│   └── <algorithm_name>/        # One per contributor/algorithm
│
├── shared/
│   ├── __init__.py
│   ├── data_loader.py           # load_dataset("name") for the shared datasets
│   ├── preprocessing.py
│   ├── evaluation.py
│   └── utils.py
│
├── data/                        # Shared by ALL algorithms (contents not in Git)
│   ├── README.md                # Table of datasets: name, source link, how to download
│   ├── raw/
│   │   └── <dataset_name>/      # One folder per dataset
│   └── processed/
│       └── <dataset_name>/
│
├── models/                      # Saved models + metrics.json (not in Git)
│   └── <algorithm_name>/
│
├── backend/                     # FastAPI goes here later
│   └── README.md                # "Placeholder: FastAPI app will live here"
├── frontend/                    # React goes here later
│   └── README.md
│
├── tests/                       # Optional for now
├── docs/
├── scripts/
│   └── setup.sh                 # Optional one-command setup
└── .github/
    └── pull_request_template.md
```