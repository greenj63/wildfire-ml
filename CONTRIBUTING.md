# Contributing

## The rules

1. Work on a branch, never directly on `main`.
2. Only edit your own algorithm folder (unless the change is meant for `shared/`).
3. Tell the group before changing anything in `shared/`; another person reviews it.
4. Never commit data, saved models, or secrets (`.gitignore` helps, but check).
5. Add a package to `requirements.txt` only if you use it, in its own small PR.
6. Python version is managed by pyenv (3.12, set in `.python-version`). Don't change that file or create extra environments.

## Git workflow (copy-paste friendly)

```bash
# 1. Get the latest code
git checkout main
git pull

# 2. Make your branch (once per piece of work)
git checkout -b yourname/algorithm-name

# 3. Do your work, then save it
git add .
git commit -m "Add linear regression training script"

# 4. Upload your branch
git push -u origin yourname/algorithm-name
```

5. On GitHub, click **Compare & pull request**, fill in the short template, and ask a
   teammate to look it over and click **Merge**.
6. Then go back to step 1 for your next piece of work.

GitHub Desktop does all of this with buttons if you prefer.

## About the auto-formatter (ruff)

After `pre-commit install`, ruff runs on every commit. If it changes your files the
commit stops. That's normal: run `git add .` and commit again.

## Before opening a pull request

- [ ] I ran my algorithm from the repo root with `python -m algorithms.<name>.train`
- [ ] My algorithm README is filled in
- [ ] I didn't commit data, models, or `.env`
