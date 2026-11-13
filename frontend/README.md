# Frontend: Wildfire Severity Predictor

A one-page React app (Vite + Leaflet) with an interactive US map of active wildfires, a
coordinate box, and a results panel. It talks to the FastAPI backend in `backend/app/`.

## Run it

Two terminals, both from the repo root. Install once: `pip install -r requirements.txt`
and `cd frontend && npm install`.

```bash
# 1. Backend (.venv active) - the API on port 8000
python -m uvicorn backend.app.main:app --reload

# 2. Frontend - the page on http://localhost:5173
cd frontend
npm run dev
```

Vite forwards `/api/...` to the backend (see `vite.config.js`), so no URLs to configure.
A prediction needs trained models: `python -m algorithms.light_gbm.train` (and the
others if you want them in the "Other models" list; untrained ones say "Not trained yet").

## How it works

- **Map:** active wildfires of **100 acres or more** from NIFC WFIGS (`GET /api/fires`,
  refreshed every 10 minutes); smaller or unsized fires are left off the map. Symbol size
  follows reported acres in five steps (100-499, 500-1,999, 2,000-9,999, 10,000-49,999,
  50,000+); the legend under the map uses the same steps (`src/fireSize.js`, which also
  holds the 100-acre cutoff).
- **Click the map, click a fire, or type coordinates** (`38.94, -123.32` or
  `(38.94, -123.32)`): the page calls `GET /api/predict?lat=..&lon=..`, which pulls live
  weather, drought and terrain data and scores every model. This takes 20 to 40 seconds
  the first time for a place (faster nearby, since the weather history is cached).
- **Results box:** LightGBM's spread rate, with the other models in an "Other models"
  dropdown; the dates of the weather and drought data used; and, if an active fire is
  within 10 km, its discovery date, containment percentage, reported size and spread rate
  so far (acres per day since discovery), plus two small charts, **Acres over time** and
  **Spread rate over time**. Click a chart to enlarge it (hover for values, Esc or × to close).
- **Fire history:** the charts come from NIFC's daily wildfire perimeters
  (`GET /api/fires/history?irwin_id=..`). A fire with fewer than two days of perimeters
  says "No day-by-day history is available". Spread rate is acres added per day between
  mapped perimeters, and acres never go down (a smaller later map is treated as a remap).
- Only the lower 48 states are supported.

## Images

| File | What |
|---|---|
| `public/images/molecule.png` | The molecule drawing, shown faded behind the formula in the header |

The fire symbol is drawn in code (`src/components/FlameIcon.jsx`), so it needs no image.

## Files

- `src/App.jsx`: page state and layout
- `src/components/`: `FireMap`, `Legend`, `CoordinateInput`, `ResultPanel`, `Header`,
  `FlameIcon`, `Chart` (SVG line and bar charts), `ExpandableChart` (preview + dialog)
- `src/coords.js`, `fireSize.js`, `format.js`, `chartMath.js`: small helpers, tested with `npm test`
- `src/styles.css`: all styling
- `src/api.js`: the three backend calls

## Commands

```bash
npm run dev      # development server
npm run build    # production build into dist/ (not committed)
npm test         # tests for the helpers
```
