"""HOW to USE the trained model. The future API will call predict().

Try it from the repo root:  python -m algorithms.<your_folder_name>.predict
"""

from pathlib import Path

import pandas as pd

from shared.utils import load_model

ALGORITHM_NAME = Path(__file__).resolve().parent.name

_model = None  # loaded once, then reused


def predict(input_data: dict):
    """Return a prediction for ONE input.

    `input_data` is a dict of {column_name: value}, e.g. {"age": 30, "income": 50000}.
    """
    global _model
    if _model is None:
        _model = load_model(ALGORITHM_NAME)
    row = pd.DataFrame([input_data])
    return _model.predict(row)[0]


if __name__ == "__main__":
    # TODO: put a real example input here
    example = {"feature_1": 0.0, "feature_2": 0.0}
    print(predict(example))
