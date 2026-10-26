# Plan: combined wildfire + drought dataset

**Status:** planned, not built yet.

Goal: one processed dataset where each row is a wildfire with the drought and weather
conditions of its county around the time it was discovered, so the two can be compared
easily. The processed file has **at most 100,000 rows**.

## Inputs

| Source | What we use |
|---|---|
| `wildfire` (FPA-FOD SQLite) | Fire columns already in `wildfire_clean.csv`, plus `FOD_ID` (unique fire ID), `FIPS_CODE`, `FIPS_NAME` |
| `droughts` (Kaggle CSVs, 2000–2020) | `fips`, `date`, weather columns, `score` |
| `county_centroids` (Census 2020 county Gazetteer, new) | `GEOID` (same code as drought `fips`), center latitude/longitude, land area |

The drought data only has county FIPS codes, no postal codes or coordinates. The
Gazetteer gives each county a center point, so pgeocode is not needed.

## Step 1: Spread rate (in `scripts/process_wildfire_data.py`)

- `DURATION_DAYS = (CONT_DATE - DISCOVERY_DATE) in days + 1`. A fire contained on the
  day it was discovered counts as 1 day. Using full dates (not day-of-year) handles fires
  that cross New Year.
- `SPREAD_RATE = FIRE_SIZE / DURATION_DAYS`, in acres per day.
- Both are empty when `CONT_DATE` is missing.
- `FIRE_SIZE` is the final size, so this is the average acres burned per day until
  containment, not a true physical spread rate.

## Step 2: Location ranges (main matching method)

- Each drought county gets its own lat/long box centered on its center point.
- Box half-width = ½ × √(county land area) + **25 km margin**. The longitude width is
  widened for latitude, since longitude degrees shrink toward the north.
- A fire is a candidate match for every county whose box contains the fire's point.
  Fires near borders will often have 2–3 candidates; that's expected.

## Step 3: Date filter

- A fire's date range is `DISCOVERY_DATE` to `CONT_DATE` (just the discovery day if
  there's no containment date).
- A drought row only matches if its date is inside that range.
- Weather columns come from the drought row on the discovery date.
- `score` is weekly, so it may be taken from **up to 7 days before discovery** (the most
  recent score on or before discovery). The score's date is saved in its own column.

## Step 4: Choosing one match

If several counties match:
1. Closest date to discovery.
2. Tie: the county with the same FIPS code as the fire.
3. Tie: the nearest county center.

## Step 5: FIPS backup

If a fire is inside no county's box, join on its `FIPS_CODE` instead, with the same date
rules. If that also fails, the fire is **dropped**: the dataset only keeps fires that
have drought data.

Each row records how it was matched:
- `MATCH_METHOD`: `latlon` or `fips`
- `MATCH_DISTANCE_KM`: distance from the fire to the matched county's center

Alaska, Hawaii, and Puerto Rico aren't in the drought data, so their fires are dropped.

## Step 6: Limit to 100,000 rows

There are about 236K natural fires in 2000–2020. After unmatched fires are dropped
(Step 5), the matched fires are sampled down to **100,000 rows** (or fewer, if fewer
matched fires exist):
- Random sample with a fixed seed (`42`) so everyone gets the same file.
- Stratified by `FIRE_SIZE_CLASS`, so the mix of small and large fires stays the same as
  in the full data.

## Output

- Script: `scripts/process_wildfire_drought_data.py`
- File: `data/processed/wildfire_drought/wildfire_drought.csv`
- Load it with:
  `load_dataset("wildfire_drought", filename="wildfire_drought.csv", processed=True)`

To stay fast, the 23M-row drought file is read in chunks, keeping only the county/date
pairs some fire needs.

## Changes to existing files when this is built

- `scripts/process_wildfire_data.py`: keep `FOD_ID`, `FIPS_CODE`, `FIPS_NAME`; add
  `DURATION_DAYS` and `SPREAD_RATE`. Teammates must re-run it, since its columns change.
- `data/README.md`: add rows for `county_centroids` and `wildfire_drought`.
