"""Collect live data for one fire into a single "sample" row the model can score.

The row uses the same raw column names as the training files, so it goes through
shared.experiment.add_derived_columns exactly like a training row does. Nothing here
touches the training data.
"""

import math
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from backend.live import gridmet, mapping, spatial, terrain, usdm
from backend.live.http import ApiError
from backend.live.wfigs import Fire

NAN = float("nan")

# Raw columns the model reads (see shared/experiment.py)
MODEL_COLUMNS = [
    "STATE", "LATITUDE", "LONGITUDE", "DISCOVERY_DOY", "DISCOVERY_TIME", "SCORE",
    "Elevation", "Slope", "Aspect", "TPI", "TRI", "Land_Cover", "NDVI-1day",
    "pr", "tmmn", "tmmx", "rmin", "rmax", "sph", "vs", "th", "srad", "vpd", "erc",
    "bi", "fm100", "fm1000",
    "sph_Percentile", "vs_Percentile", "fm100_Percentile", "bi_Percentile",
    "vpd_Percentile", "erc_Percentile",
    "OWNER_DESCR", "NWCG_REPORTING_AGENCY", "No_FireStation_10.0km",
    "No_FireStation_20.0km", "Ecoregion_NA_L2CODE", "Population",
]  # fmt: skip

# Information about the fire and the data, not used by the model
META_COLUMNS = [
    "FIRE_NAME", "IRWIN_ID", "DISCOVERY_UTC", "DISCOVERY_DATE", "COUNTY_FIPS",
    "REPORTED_ACRES", "WEATHER_DATE", "SCORE_DATE", "MISSING_FEATURES", "WARNINGS",
]  # fmt: skip

EXPECTED_ERRORS = (ApiError, ValueError, KeyError, IndexError, TypeError)


class _Collector:
    """Runs one data source and records a warning instead of failing the whole fire."""

    def __init__(self):
        self.warnings: list[str] = []

    def run(self, label: str, func: Callable, default=None):
        try:
            return func()
        except EXPECTED_ERRORS as error:
            self.warnings.append(f"{label}: {error}")
            return default


def _number(value) -> float:
    return NAN if value is None else float(value)


def build_sample(
    fire: Fire, skip_percentiles: bool = False, with_ndvi: bool = False
) -> dict:
    """Pull every live source for `fire` and return one sample row (a dict)."""
    lat, lon = fire.latitude, fire.longitude
    local = mapping.local_discovery(fire.discovered, lon, fire.state)
    on = local.date()
    collect = _Collector()

    with ThreadPoolExecutor(max_workers=6) as pool:
        weather_job = pool.submit(
            collect.run, "gridMET weather", lambda: gridmet.fetch_weather(lat, lon, on)
        )
        terrain_job = pool.submit(
            collect.run, "3DEP terrain", lambda: terrain.fetch_terrain(lat, lon), {}
        )
        cover_job = pool.submit(
            collect.run, "NLCD land cover", lambda: spatial.fetch_land_cover(lat, lon)
        )
        eco_job = pool.submit(
            collect.run, "EPA ecoregion", lambda: spatial.fetch_ecoregion(lat, lon)
        )
        stations_job = pool.submit(
            collect.run,
            "fire stations",
            lambda: spatial.fetch_fire_station_counts(lat, lon),
        )
        ndvi_job = (
            pool.submit(
                collect.run, "MODIS NDVI", lambda: spatial.fetch_ndvi(lat, lon, on)
            )
            if with_ndvi
            else None
        )

        state, fips = fire.state, fire.county_fips
        if not (state and fips):  # WFIGS sometimes omits them
            found = collect.run("Census county", lambda: spatial.fetch_county(lat, lon))
            if found:
                state, fips = state or found[0], fips or found[1]

        # These two need the results above
        weather, weather_date = weather_job.result() or ({}, None)
        percentile_job = None
        if weather and not skip_percentiles:
            percentile_job = pool.submit(
                collect.run,
                "gridMET percentiles",
                lambda: gridmet.fetch_percentile_bins(lat, lon, weather_date, weather),
                {},
            )
        drought_job = (
            pool.submit(
                collect.run,
                "Drought Monitor",
                lambda: usdm.fetch_drought_score(fips, on),
            )
            if fips
            else None
        )

        land = terrain_job.result()
        land_cover = cover_job.result()
        ecoregion = eco_job.result()
        stations = stations_job.result()
        ndvi = ndvi_job.result() if ndvi_job else None
        percentiles = percentile_job.result() if percentile_job else {}
        drought = drought_job.result() if drought_job else None

    score, score_date = drought if drought else (None, None)
    row = {
        "STATE": state,
        "LATITUDE": lat,
        "LONGITUDE": lon,
        "DISCOVERY_DOY": on.timetuple().tm_yday,
        "DISCOVERY_TIME": local.hour * 100 + local.minute,
        "SCORE": _number(score),
        "Elevation": _number(land.get("Elevation")),
        "Slope": _number(land.get("Slope")),
        "Aspect": _number(land.get("Aspect")),
        "TPI": _number(land.get("TPI")),
        "TRI": _number(land.get("TRI")),
        "Land_Cover": _number(land_cover),
        "NDVI-1day": _number(ndvi),
        "OWNER_DESCR": mapping.owner_description(fire.owner_category),
        "NWCG_REPORTING_AGENCY": mapping.reporting_agency(fire.protecting_agency),
        "No_FireStation_10.0km": _number(stations[0]) if stations else NAN,
        "No_FireStation_20.0km": _number(stations[1]) if stations else NAN,
        "Ecoregion_NA_L2CODE": ecoregion,
        "Population": NAN,
    }
    for key in gridmet.VARIABLES:
        row[key] = _number(weather.get(key))
    for key in gridmet.PERCENTILE_VARIABLES:
        row[f"{key}_Percentile"] = percentiles.get(key)

    missing = [
        column
        for column in MODEL_COLUMNS
        if row[column] is None
        or (isinstance(row[column], float) and math.isnan(row[column]))
    ]
    if skip_percentiles:
        collect.warnings.append("percentiles skipped on request")
    row |= {
        "FIRE_NAME": fire.name,
        "IRWIN_ID": fire.irwin_id,
        "DISCOVERY_UTC": fire.discovered.strftime("%Y-%m-%d %H:%M"),
        "DISCOVERY_DATE": on.isoformat(),
        "COUNTY_FIPS": fips,
        "REPORTED_ACRES": _number(fire.reported_acres),
        "WEATHER_DATE": weather_date.isoformat() if weather_date else None,
        "SCORE_DATE": score_date.isoformat() if score_date else None,
        "MISSING_FEATURES": ";".join(missing),
        "WARNINGS": " | ".join(collect.warnings),
    }
    return row
