"""The API the React frontend calls.

Run from the repo root (with .venv active):

    python -m uvicorn backend.app.main:app --reload
"""

from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Query

from backend.app import fires as fire_store
from backend.app import predictor
from backend.live import history
from backend.live.http import ApiError
from backend.live.sample import MODEL_COLUMNS, build_sample
from backend.live.wfigs import Fire

app = FastAPI(title="Wildfire Severity Predictor API")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/fires")
def get_fires() -> dict:
    """Active wildfires (lower 48) with their reported size in acres."""
    try:
        fires = fire_store.active_fires()
    except ApiError as error:
        raise HTTPException(
            502, "Could not reach the NIFC wildfire service."
        ) from error
    now = datetime.now(UTC)
    return {
        "updated": now.isoformat(),
        "fires": [fire_store.fire_summary(fire, now) for fire in fires],
    }


@app.get("/api/fires/history")
def get_fire_history(irwin_id: str = Query(max_length=64)) -> dict:
    """Acres and spread rate by day for one fire (empty list if NIFC has no history)."""
    guid = history.normalize_irwin_id(irwin_id)
    if guid is None:
        raise HTTPException(400, "That is not a valid fire id.")
    try:
        series = history.fetch_history(guid)
    except ApiError as error:
        raise HTTPException(
            502, "Could not reach the NIFC perimeter service."
        ) from error
    return {"irwin_id": guid, "series": series}


@app.get("/api/predict")
def get_prediction(
    lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180)
) -> dict:
    """Live prediction for a point: pulls current data, then scores every model."""
    if not fire_store.in_lower_48(lat, lon):
        raise HTTPException(
            400, "Pick a location inside the continental United States."
        )
    now = datetime.now(UTC)
    sample = build_sample(Fire("MAP POINT", lat, lon, now))
    models = predictor.predict_all({col: sample[col] for col in MODEL_COLUMNS})

    nearby = None
    try:
        found = fire_store.nearest_fire(lat, lon, fire_store.active_fires())
    except ApiError:
        found = None  # the prediction is still useful without the fire list
    if found:
        fire, km = found
        nearby = {**fire_store.fire_summary(fire, now), "distance_km": round(km, 1)}

    weather_date, drought_date = sample["WEATHER_DATE"], sample["SCORE_DATE"]
    return {
        "location": {"latitude": lat, "longitude": lon},
        "primary_model": predictor.PRIMARY_MODEL,
        "models": models,
        "weather_date": weather_date,
        "drought_date": drought_date,
        "nearby_fire": nearby,
        "notice": (
            None
            if weather_date and drought_date
            else "Some live data was unavailable, so this prediction is less reliable."
        ),
    }
