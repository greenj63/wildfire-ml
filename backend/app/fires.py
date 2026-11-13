"""Active wildfires for the map, and finding the one nearest a clicked point."""

import math
import threading
import time
from datetime import UTC, datetime

from backend.live.wfigs import Fire, fetch_active_fires

# south, north, west, east. The models and live data only cover the lower 48 states.
LOWER_48 = (24.0, 50.0, -125.0, -66.0)
CACHE_SECONDS = 600
NEARBY_KM = 10.0
EARTH_RADIUS_KM = 6371.0

_cache = {"fetched": 0.0, "fires": []}
_lock = threading.Lock()


def in_lower_48(lat: float, lon: float) -> bool:
    south, north, west, east = LOWER_48
    return south <= lat <= north and west <= lon <= east


def active_fires(now: float | None = None) -> list[Fire]:
    """Active lower-48 fires, refreshed at most every CACHE_SECONDS.

    If WFIGS is down, the last good list is kept rather than emptying the map.
    """
    now = time.time() if now is None else now
    with _lock:
        if now - _cache["fetched"] > CACHE_SECONDS or not _cache["fires"]:
            try:
                fires = fetch_active_fires()
                _cache["fires"] = [
                    f for f in fires if in_lower_48(f.latitude, f.longitude)
                ]
                _cache["fetched"] = now
            except Exception:
                if not _cache["fires"]:
                    raise
        return list(_cache["fires"])


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance (haversine)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (
        math.sin((p2 - p1) / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def nearest_fire(lat: float, lon: float, fires: list[Fire], max_km: float = NEARBY_KM):
    """(fire, distance in km) for the closest fire within `max_km`, else None."""
    best = None
    for fire in fires:
        d = distance_km(lat, lon, fire.latitude, fire.longitude)
        if d <= max_km and (best is None or d < best[1]):
            best = (fire, d)
    return best


def spread_so_far(fire: Fire, now: datetime) -> float | None:
    """Acres per day since discovery.

    Counts days the way the training data does (a fire found and contained on the
    same day lasted 1 day), so it compares with the model's prediction.
    """
    if not fire.reported_acres:
        return None
    elapsed_days = max((now - fire.discovered).total_seconds(), 0) / 86400
    return fire.reported_acres / (math.floor(elapsed_days) + 1)


def fire_summary(fire: Fire, now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    rate = spread_so_far(fire, now)
    return {
        "name": fire.name,
        "latitude": round(fire.latitude, 5),
        "longitude": round(fire.longitude, 5),
        "state": fire.state,
        "acres": fire.reported_acres,
        "discovered": fire.discovered.isoformat(),
        "percent_contained": fire.percent_contained,
        "irwin_id": fire.irwin_id or None,
        "spread_so_far": None if rate is None else round(rate, 2),
    }
