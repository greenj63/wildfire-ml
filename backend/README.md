# Backend

Two things live here: the **FastAPI app** (`backend/app/`) that the React page calls, and
the **live data code** (`backend/live/`) that pulls current data, builds a sample, and
predicts with a trained model.

## API (for the frontend)

```bash
python -m uvicorn backend.app.main:app --reload     # http://127.0.0.1:8000/docs
```

| Route | Returns |
|---|---|
| `GET /api/fires` | Active lower-48 wildfires from NIFC WFIGS with reported acres, discovery time and containment percent (cached 10 minutes) |
| `GET /api/fires/history?irwin_id=..` | Acres and spread rate by day for one fire, from NIFC daily perimeters (cached 1 hour; empty list if fewer than 2 days exist) |
| `GET /api/predict?lat=..&lon=..` | Spread rate from every algorithm (LightGBM first; untrained ones are marked), the weather and drought data dates, and the nearest active fire within 10 km with its size, containment, discovery date and spread rate so far |

Run the page with `npm run dev` in `frontend/` (see its README). A prediction takes about
30 seconds for a new place because of the live data pulls.

## Live predictions (command line)

From the repo root, with `.venv` active and the model trained
(`python -m algorithms.light_gbm.train`):

```bash
python -m backend.live_predict                      # newest fires from NIFC WFIGS
python -m backend.live_predict --hours 72 --limit 10
python -m backend.live_predict --point 38.56 -119.91 --when "2026-11-10 18:00"   # UTC
python -m backend.live_predict --algorithm random_forest
python -m backend.live_predict --sample data/processed/live_samples/<file>.csv   # re-score
```

Options: `--skip-percentiles` (much faster, about 20 s per fire saved) and `--with-ndvi`.

It saves two files in `data/processed/live_samples/` (ignored by Git, never added to
the training split): `live_sample_<time>.csv` (the model inputs plus which ones were
missing and any warnings) and `live_predictions_<time>.csv` (the same plus the
prediction in acres per day).

## Where each input comes from

Code is in `backend/live/`. No keys, and no packages beyond `requirements.txt`.

| Model input | Source | Notes |
|---|---|---|
| Location, discovery time, state, county, owner, agency | NIFC WFIGS incidents | Time converted to the fire's local clock |
| `pr`, `tmmn`, `tmmx`, `rmin`, `rmax`, `sph`, `vs`, `th`, `srad`, `vpd`, `erc`, `bi`, `fm100`, `fm1000` | gridMET (THREDDS) | About 2 days behind real time; the latest day is used |
| `*_Percentile` (6) | gridMET history | Every other year of 1991-2020, within 15 days; matched 29/36 training bins exactly, never more than one bin off |
| `SCORE` | US Drought Monitor | Cumulative D0-D4 percent / 100; matched the training score on the 2 fires checked |
| `Elevation`, `Slope`, `Aspect`, `TPI`, `TRI` | USGS 3DEP | Computed from a 3x3 grid, 30 m apart |
| `Land_Cover` | MRLC NLCD 2021 | About 82% agreement with the stored class (land changes) |
| `Ecoregion_NA_L2CODE` | EPA Level II ecoregions | |
| `No_FireStation_10.0km`, `No_FireStation_20.0km` | USGS structures | **Runs low**: roughly half the training counts |
| `NDVI-1day` | MODIS (`--with-ndvi` only) | Off by default: only loosely matches the training product |
| `Population` | none | Always missing |

A missing input does not stop the run: the models fill it with the training median.
The output lists every missing input, so check it before trusting a prediction.

## Limits

- Lower 48 states only (gridMET, NLCD, and the training data cover nothing else).
- The models score R2 of about 0.28, and training used 2000-2020 fires, so treat
  predictions as rough rankings. Compare with the reported size as the fire grows.
- Fire stations, NDVI, and Population differ from the training source, so there is
  some drift. Weather, drought, and terrain were checked against stored rows.
- The services are public and can be slow or down. A failing source is reported in
  `WARNINGS` and left missing; the run continues.

Tests (no network): `python -m pytest tests/test_live.py`
