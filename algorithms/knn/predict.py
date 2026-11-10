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
            # Location and timing
            "STATE": "CA",
            "LATITUDE": 37.7444,
            "LONGITUDE": -119.7464,
            "DISCOVERY_DOY": 165,
            "DISCOVERY_TIME": 740,
            # Drought (weekly county score, 0-5)
            "SCORE": 2.0,
            # Terrain and vegetation
            "Elevation": 1964.0,
            "Slope": 11.0,
            "Aspect": 177.0,
            "TPI": -1.375,
            "TRI": 16.401,
            "Land_Cover": 52,
            "NDVI-1day": 0.14,
            # Weather at the fire that day (temperatures in Kelvin)
            "pr": 0.0,
            "tmmn": 276.7,
            "tmmx": 287.6,
            "rmin": 38.7,
            "rmax": 73.0,
            "sph": 0.00487,
            "vs": 2.4,
            "th": 210.0,
            "srad": 286.7,
            "vpd": 0.56,
            "erc": 60.0,
            "bi": 41.0,
            "fm100": 9.1,
            "fm1000": 10.1,
            "sph_Percentile": "30-50%",
            "vs_Percentile": "30-50%",
            "fm100_Percentile": "70-90%",
            "bi_Percentile": "30-50%",
            "vpd_Percentile": "5-10%",
            "erc_Percentile": "30-50%",
            # Who responds, and region
            "OWNER_DESCR": "NPS",
            "NWCG_REPORTING_AGENCY": "NPS",
            "No_FireStation_10.0km": 1.0,
            "No_FireStation_20.0km": 13.0,
            "Ecoregion_NA_L2CODE": 6.2,
            "Population": 0.0,
        }
    print(f"Predicted spread rate: {predict(example):.3f} acres/day")
