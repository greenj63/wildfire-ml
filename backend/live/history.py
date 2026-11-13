"""Acres-over-time for one fire, from NIFC's daily wildfire perimeters (WFIGS)."""

import re
import threading
import time
from datetime import UTC, datetime

from backend.live.http import ApiError, get_json

SERVICE = (
    "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/"
    "WFIGS_Daily_Perimeters_Public/FeatureServer/0/query"
)
GUID = re.compile(r"^\{?([0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12})\}?$")
CACHE_SECONDS = 3600
FIELDS = (
    "poly_PolygonDateTime,poly_CreateDate,poly_DateCurrent,poly_GISAcres,"
    "poly_DeleteThis,poly_FeatureCategory"
)

_cache: dict[str, tuple[float, list[dict]]] = {}
_lock = threading.Lock()


def normalize_irwin_id(value: str) -> str | None:
    """The id as "{ABC...}" in upper case, or None if it is not a GUID.

    The id goes into a query, so anything else is refused.
    """
    match = GUID.match(value.strip())
    return "{" + match.group(1).upper() + "}" if match else None


def _usable(attributes: dict) -> bool:
    deleted = str(attributes.get("poly_DeleteThis") or "").strip().lower()
    category = attributes.get("poly_FeatureCategory")
    return not deleted.startswith("yes") and (
        category is None or str(category).startswith("Wildfire")
    )


def build_series(records: list[dict]) -> list[dict]:
    """[{"date", "acres", "rate"}] one point per day.

    A day's acres is its largest perimeter, and acres never go down (a smaller later
    map is a remap, not a shrinking fire). "rate" is acres per day since the previous
    point, so it is None on the first one.
    """
    by_day: dict = {}
    for attributes in records:
        if not _usable(attributes):
            continue
        acres = attributes.get("poly_GISAcres")
        moment = (
            attributes.get("poly_PolygonDateTime")
            or attributes.get("poly_CreateDate")
            or attributes.get("poly_DateCurrent")
        )
        if acres is None or acres < 0 or not moment:
            continue
        day = datetime.fromtimestamp(moment / 1000, UTC).date()
        by_day[day] = max(by_day.get(day, 0.0), float(acres))

    series, best, previous_day = [], 0.0, None
    for day in sorted(by_day):
        best = max(best, by_day[day])
        rate = None
        if previous_day is not None:
            rate = (best - series[-1]["acres"]) / (day - previous_day).days
        series.append(
            {
                "date": day.isoformat(),
                "acres": round(best, 1),
                "rate": None if rate is None else round(rate, 1),
            }
        )
        previous_day = day
    return series


def fetch_history(irwin_id: str, now: float | None = None) -> list[dict]:
    """The fire's daily series (empty if NIFC has fewer than 2 days of perimeters)."""
    guid = normalize_irwin_id(irwin_id)
    if guid is None:
        raise ValueError("Not a valid IRWIN id")
    now = time.time() if now is None else now
    with _lock:
        hit = _cache.get(guid)
        if hit and now - hit[0] < CACHE_SECONDS:
            return hit[1]
    data = get_json(
        SERVICE,
        {
            "where": f"poly_IRWINID='{guid}' OR attr_IrwinID='{guid}'",
            "outFields": FIELDS,
            "returnGeometry": "false",
            "resultRecordCount": 2000,
            "f": "json",
        },
    )
    if "features" not in data:
        raise ApiError("Unexpected response from the perimeter service")
    series = build_series([f["attributes"] for f in data["features"]])
    series = series if len(series) >= 2 else []
    with _lock:
        _cache[guid] = (now, series)
    return series
