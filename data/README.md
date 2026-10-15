# Shared datasets

All algorithms read data from here. Data files are NOT committed to Git.
To use a dataset: download it, put the files in `data/raw/<dataset_name>/`,
then load it in code with `shared.data_loader.load_dataset("<dataset_name>")`.

Keep folder names `lowercase_with_underscores`.

| Dataset name | Source link | Files expected | Added by |
|---|---|---|---|
| _example_dataset_ | https://www.kaggle.com/... | `data.csv` in `data/raw/example_dataset/` | your name |

(Add a row whenever you add a dataset.)
