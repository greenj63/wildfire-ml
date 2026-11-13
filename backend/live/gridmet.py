"""gridMET (University of Idaho) weather and fire danger at a point.

Served by the Northwest Knowledge Network THREDDS NetCDF Subset Service as CSV. The
service returns the raw packed integers, so every variable is unpacked here with the
scale and offset from its dataset.xml. gridMET is about 2 days behind real time.
"""

import csv
import io
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

from backend.live.http import ApiError, get_text

URL = (
    "https://thredds.northwestknowledge.net/thredds/ncss/"
    "agg_met_{key}_1979_CurrentYear_CONUS.nc"
)
FILL_VALUE = 32767

# key (same as the training column): (netCDF variable, scale, offset)
VARIABLES = {
    "pr": ("precipitation_amount", 0.1, 0.0),
    "tmmn": ("daily_minimum_temperature", 0.1, 210.0),
    "tmmx": ("daily_maximum_temperature", 0.1, 220.0),
    "rmin": ("daily_minimum_relative_humidity", 0.1, 0.0),
    "rmax": ("daily_maximum_relative_humidity", 0.1, 0.0),
    "sph": ("daily_mean_specific_humidity", 1e-5, 0.0),
    "vs": ("daily_mean_wind_speed", 0.1, 0.0),
    "th": ("daily_mean_wind_direction", 1.0, 0.0),
    "srad": ("daily_mean_shortwave_radiation_at_surface", 0.1, 0.0),
    "vpd": ("daily_mean_vapor_pressure_deficit", 0.01, 0.0),
    "erc": ("daily_mean_energy_release_component-g", 1.0, 0.0),
    "bi": ("daily_mean_burning_index_g", 1.0, 0.0),
    "fm100": ("dead_fuel_moisture_100hr", 0.1, 0.0),
    "fm1000": ("dead_fuel_moisture_1000hr", 0.1, 0.0),
}

# Variables the model uses as "how unusual was today" percentiles
PERCENTILE_VARIABLES = ("sph", "vs", "fm100", "bi", "vpd", "erc")

# Baseline for the percentiles: every other year of 1991-2020, within 15 days of the
# same calendar day. On 6 training fires this matched the stored bin for 29 of 36
# values and was never more than one bin off. A full 30-year pull is far too slow.
BASELINE_YEARS = range(1991, 2021, 2)
WINDOW_DAYS = 15
PERCENTILE_EDGES = [
    (10, "<10%"),
    (30, "10-30%"),
    (50, "30-50%"),
    (70, "50-70%"),
    (90, "70-90%"),
]
MAX_WORKERS = 8

_baseline_cache: dict = {}


def _fetch_series(key: str, lat: float, lon: float, start: date, end: date) -> dict:
    """{date: unpacked value} for one variable. Missing days are left out."""
    name, scale, offset = VARIABLES[key]
    text = get_text(
        URL.format(key=key),
        {
            "var": name,
            "latitude": f"{lat:.5f}",
            "longitude": f"{lon:.5f}",
            "time_start": f"{start:%Y-%m-%d}T00:00:00Z",
            "time_end": f"{end:%Y-%m-%d}T00:00:00Z",
            "accept": "csv",
        },
        timeout=120,
    )
    series = {}
    for row in list(csv.reader(io.StringIO(text)))[1:]:
        try:
            packed = float(row[3])
        except (IndexError, ValueError):
            continue
        if math.isnan(packed) or packed >= FILL_VALUE:
            continue
        series[date.fromisoformat(row[0][:10])] = packed * scale + offset
    return series


def fetch_weather(lat: float, lon: float, on: date) -> tuple[dict, date]:
    """Latest gridMET values on or before `on`: ({key: value}, date they are for)."""
    start = on - timedelta(days=7)
    with ThreadPoolExecutor(MAX_WORKERS) as pool:
        all_series = pool.map(
            lambda key: _fetch_series(key, lat, lon, start, on), VARIABLES
        )
        results = dict(zip(VARIABLES, all_series, strict=True))
    days = set.intersection(*(set(series) for series in results.values()))
    if not days:
        raise ApiError(f"gridMET has no data for ({lat}, {lon}) the week up to {on}")
    weather_date = max(days)
    return {key: results[key][weather_date] for key in VARIABLES}, weather_date


def _baseline_values(key: str, lat: float, lon: float, on: date) -> list[float]:
    """The variable's values within WINDOW_DAYS of `on`'s day, in baseline years."""
    cell = (key, round(lat * 24), round(lon * 24), on.month, on.day)  # ~4 km grid cell
    if cell in _baseline_cache:
        return _baseline_cache[cell]

    def one_year(year: int) -> list[float]:
        try:
            center = on.replace(year=year)
        except ValueError:  # Feb 29
            center = on.replace(year=year, day=28)
        window = timedelta(days=WINDOW_DAYS)
        return list(
            _fetch_series(key, lat, lon, center - window, center + window).values()
        )

    with ThreadPoolExecutor(MAX_WORKERS) as pool:
        values = [v for chunk in pool.map(one_year, BASELINE_YEARS) for v in chunk]
    _baseline_cache[cell] = values
    return values


def percentile_bin(value: float, baseline: list[float]) -> str | None:
    """Where `value` falls in the baseline, as the training bins ("<10%".. ">90%")."""
    if not baseline:
        return None
    below = sum(v < value for v in baseline)
    at_or_below = sum(v <= value for v in baseline)
    percentile = 100 * (below + at_or_below) / (2 * len(baseline))
    for edge, label in PERCENTILE_EDGES:
        if percentile < edge:
            return label
    return ">90%"


def fetch_percentile_bins(lat: float, lon: float, weather_date: date, weather: dict):
    """{"sph": "30-50%", ...} for the six percentile variables."""
    return {
        key: percentile_bin(weather[key], _baseline_values(key, lat, lon, weather_date))
        for key in PERCENTILE_VARIABLES
    }
