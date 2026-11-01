"""HOW to USE the trained model. The future API will call predict().

Try it from the repo root:  python -m algorithms.<your_folder_name>.predict
"""

from pathlib import Path

import numpy as np
import pandas as pd

from shared.experiment import FEATURES, add_derived_columns
from shared.utils import load_model

ALGORITHM_NAME = Path(__file__).resolve().parent.name

_model = None  # loaded once, then reused


def predict(input_data: dict) -> float:
    """Return the predicted spread rate (acres per day) for ONE newly reported fire.

    `input_data` has the fire's location, discovery day/time, that day's weather, and
    the drought score (see the example below). The model predicts log(1 + spread
    rate), so the result is converted back to acres per day.
    """
    global _model
    if _model is None:
        _model = load_model(ALGORITHM_NAME)
    row = add_derived_columns(pd.DataFrame([input_data]))[FEATURES]
    return float(np.expm1(_model.predict(row)[0]))


if __name__ == "__main__":
    # A real fire from the data (CA, 2020). Its actual spread rate was
    # 0.01 acres/day.
    example = {
        "STATE": "CA",
        "LATITUDE": 37.7444,
        "LONGITUDE": -119.7464,
        "DISCOVERY_DOY": 165,
        "DISCOVERY_TIME": 740,
        "PRECTOT": 0.04,
        "PS": 83.93,
        "QV2M": 4.79,
        "T2M": 9.67,
        "T2MDEW": 0.73,
        "T2MWET": 0.46,
        "T2M_MAX": 16.88,
        "T2M_MIN": 2.21,
        "T2M_RANGE": 14.66,
        "TS": 10.33,
        "WS10M": 2.42,
        "WS10M_MAX": 4.44,
        "WS10M_MIN": 0.15,
        "WS10M_RANGE": 4.29,
        "WS50M": 3.13,
        "WS50M_MAX": 5.17,
        "WS50M_MIN": 0.1,
        "WS50M_RANGE": 5.06,
        "SCORE": 2.0,
    }
    print(f"Predicted spread rate: {predict(example):.3f} acres/day")
