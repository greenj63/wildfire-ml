"""HOW the model learns. Run from the repo root:

python -m algorithms.<your_folder_name>.train
"""

from pathlib import Path

from shared.data_loader import load_dataset, split_data
from shared.evaluation import evaluate_classification  # or evaluate_regression
from shared.utils import save_metrics, save_model, set_random_seed

from .model import build_model

# The folder name is used automatically, so you never have to rename it here.
ALGORITHM_NAME = Path(__file__).resolve().parent.name

# TODO: set these for your project
DATASET_NAME = "your_dataset_name"  # folder inside data/raw/
TARGET_COLUMN = "target"  # the column you want to predict


def main() -> None:
    set_random_seed()

    # 1. Load data (and add preprocessing from shared/preprocessing.py if needed)
    df = load_dataset(DATASET_NAME)

    # 2. Split into training and test sets
    X_train, X_test, y_train, y_test = split_data(df, TARGET_COLUMN)

    # 3. Build and train the model
    model = build_model()
    model.fit(X_train, y_train)

    # 4. Evaluate (switch to evaluate_regression for regression problems)
    metrics = evaluate_classification(y_test, model.predict(X_test))
    print(metrics)

    # 5. Save the model and its results to models/<algorithm_name>/
    save_model(model, ALGORITHM_NAME)
    save_metrics(metrics, ALGORITHM_NAME)


if __name__ == "__main__":
    main()
