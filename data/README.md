# Shared datasets

All algorithms read data from here. **Data files are NOT committed to Git**, so each
person downloads the data once and builds the processed files by running a script.

Folder names use `lowercase_with_underscores`. The dataset name is the folder name
under `data/raw/`, and it's what you pass to `load_dataset("<dataset_name>")`.

## Datasets

| Dataset name | Source | Raw file (download this) | Processed file (made by script) | Script | Added by |
|---|---|---|---|---|---|
| `wildfire` | https://www.kaggle.com/datasets/braddarrow/23-million-wildfires | `data/raw/wildfire/FPA_FOD_20221014.sqlite` | `data/processed/wildfire/wildfire_clean.csv` | `scripts/process_wildfire_data.py` | Arlim Macaldo |
| `droughts` | https://www.kaggle.com/datasets/cdminix/us-drought-meteorological-data | `test_timeseries.csv`, `train_timeseries.csv`, `validation_timeseries.csv` | `data/processed/droughts/drought_clean.csv` | `scripts/process_drought_data.py` | Arlim Macaldo |

(Add a row whenever you add a dataset or a new processed file.)

## Getting a dataset set up (every teammate)

1. Download the dataset from the source link. If it comes as a zip, unzip it.
2. Put the raw file in the exact folder shown in the table, for example
   `data/raw/wildfire/FPA_FOD_20221014.sqlite`.
3. From the repo root, with `.venv` active, run the script listed in the table:
   `python -m scripts.process_wildfire_data`
4. Load the processed file in your algorithm:
   `load_dataset("wildfire", filename="wildfire_clean.csv", processed=True)`

## When a processing script changes

Processed files aren't in Git, so they don't update when the script does. If a script
change affects its output (different columns, cleaning, or new files):

```bash
git checkout main
git pull
python -m scripts.process_wildfire_data
```

Then re-train any algorithm that uses that file. The person who changes a script should
say so in the PR description and tell the group.

## Adding a new dataset

1. Pick a folder name (`lowercase_with_underscores`) and put the raw file in `data/raw/<name>/`.
2. Write a script in `scripts/prepare_<name>.py` that reads the raw data and writes to `data/processed/<name>/`.
3. Add a row to the table above, filling in every column.
4. Open a PR. Don't commit the data files.