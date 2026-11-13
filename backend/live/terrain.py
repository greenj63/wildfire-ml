"""Terrain at a point from the USGS 3DEP elevation service.

Samples a 3x3 grid of elevations 30 m apart, then computes the same measures as the
training data: slope and aspect (Horn's method), TPI (center minus the mean of its 8
neighbors) and TRI (Riley's index: root of the summed squared differences).
"""

import json
import math

from backend.live.http import ApiError, get_json

URL = "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/getSamples"
CELL_METERS = 30.0
METERS_PER_DEGREE_LAT = 111_320.0
FLAT_SLOPE_DEGREES = 0.1  # below this the ground has no aspect (stored as -1)


def terrain_from_grid(z: list[list[float]], cell: float = CELL_METERS) -> dict:
    """Terrain measures from a 3x3 elevation grid (rows run north to south)."""
    (a, b, c), (d, e, f), (g, h, i) = z
    d_east = ((c + 2 * f + i) - (a + 2 * d + g)) / (8 * cell)
    d_north = ((a + 2 * b + c) - (g + 2 * h + i)) / (8 * cell)
    slope = math.degrees(math.atan(math.hypot(d_east, d_north)))
    if slope < FLAT_SLOPE_DEGREES:
        aspect = -1.0
    else:  # compass bearing the slope faces (downhill direction)
        aspect = math.degrees(math.atan2(-d_east, -d_north)) % 360
    neighbors = [a, b, c, d, f, g, h, i]
    return {
        "Elevation": e,
        "Slope": slope,
        "Aspect": aspect,
        "TPI": e - sum(neighbors) / 8,
        "TRI": math.sqrt(sum((n - e) ** 2 for n in neighbors)),
    }


def fetch_terrain(lat: float, lon: float) -> dict:
    """Elevation (m), Slope (degrees), Aspect (degrees, -1 = flat), TPI, TRI."""
    d_lat = CELL_METERS / METERS_PER_DEGREE_LAT
    d_lon = CELL_METERS / (METERS_PER_DEGREE_LAT * math.cos(math.radians(lat)))
    offsets = [(row, col) for row in (1, 0, -1) for col in (-1, 0, 1)]  # north first
    points = [[lon + col * d_lon, lat + row * d_lat] for row, col in offsets]
    data = get_json(
        URL,
        {
            "geometry": json.dumps(
                {"points": points, "spatialReference": {"wkid": 4326}}
            ),
            "geometryType": "esriGeometryMultipoint",
            "returnFirstValueOnly": "true",
            "interpolation": "RSP_BilinearInterpolation",
            "f": "json",
        },
        timeout=120,
    )
    values = {}
    for sample in data.get("samples", []):
        try:
            values[sample["locationId"]] = float(sample["value"])
        except (KeyError, TypeError, ValueError):
            pass
    if len(values) != 9:
        raise ApiError(f"3DEP has no elevation grid at ({lat}, {lon})")
    flat = [values[k] for k in range(9)]
    return terrain_from_grid([flat[0:3], flat[3:6], flat[6:9]])
