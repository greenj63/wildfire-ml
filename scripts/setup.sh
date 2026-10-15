#!/usr/bin/env bash
# One-command setup for Mac/Linux using pyenv. Run from the repo root:
#   bash scripts/setup.sh
set -e

if ! command -v pyenv >/dev/null 2>&1; then
  echo "pyenv not found. Install it first: https://github.com/pyenv/pyenv#installation"
  exit 1
fi

# Install Python 3.12 if pyenv doesn't have it yet
if ! pyenv versions --bare | grep -q "^3\\.12"; then
  pyenv install 3.12
fi
pyenv local 3.12

python --version
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
pre-commit install
echo "Done. Activate the environment with: source .venv/bin/activate"
