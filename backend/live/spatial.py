"""Point lookups: land cover, ecoregion, fire stations, county, and (optional) NDVI."""

from datetime import date, timedelta

from backend.live.http import ApiError, get_json

NLCD_URL = "https://www.mrlc.gov/geoserver/mrlc_display/NLCD_2021_Land_Cover_L48/wms"
ECOREGION_URL = "https://clmapper.epa.gov/arcgis/rest/services/Deposition/Overlays/MapServer/1/query"
STATIONS_URL = (
    "https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/16/query"
)
CENSUS_URL = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
MODIS_URL = "https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset"

# NLCD classes that appear in the training data
NLCD_CLASSES = {11, 12, 21, 22, 23, 24, 31, 32, 33, 41, 42, 43, 51, 52, 71, 81, 82, 83,
                84, 90, 91, 92, 95}  # fmt: skip


def fetch_land_cover(lat: float, lon: float) -> int | None:
    """NLCD 2021 land cover class (e.g. 42 = evergreen forest) at the point."""
    half = 0.0005
    data = get_json(
        NLCD_URL,
        {
            "service": "WMS",
            "version": "1.1.1",
            "request": "GetFeatureInfo",
            "layers": "NLCD_2021_Land_Cover_L48",
            "query_layers": "NLCD_2021_Land_Cover_L48",
            "styles": "",
            "srs": "EPSG:4326",
            "bbox": f"{lon - half},{lat - half},{lon + half},{lat + half}",
            "width": 101,
            "height": 101,
            "x": 50,
            "y": 50,
            "info_format": "application/json",
        },
    )
    features = data.get("features") or []
    if not features:
        return None
    value = int(features[0]["properties"].get("PALETTE_INDEX", -1))
    return value if value in NLCD_CLASSES else None


def fetch_ecoregion(lat: float, lon: float) -> str | None:
    """EPA Level II ecoregion code, e.g. "6.2"."""
    data = get_json(
        ECOREGION_URL,
        {
            "f": "json",
            "geometry": f"{lon},{lat}",
            "geometryType": "esriGeometryPoint",
            "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "NA_L2CODE",
            "returnGeometry": "false",
        },
    )
    features = data.get("features") or []
    return features[0]["attributes"]["NA_L2CODE"] if features else None


def fetch_fire_station_counts(lat: float, lon: float) -> tuple[int, int]:
    """Fire/EMS stations within 10 km and 20 km (USGS structures).

    This layer lists fewer stations than the training source, so counts run low.
    """
    counts = []
    for meters in (10_000, 20_000):
        data = get_json(
            STATIONS_URL,
            {
                "f": "json",
                "geometry": f"{lon},{lat}",
                "geometryType": "esriGeometryPoint",
                "inSR": 4326,
                "spatialRel": "esriSpatialRelIntersects",
                "distance": meters,
                "units": "esriSRUnit_Meter",
                "returnCountOnly": "true",
            },
        )
        counts.append(int(data["count"]))
    return counts[0], counts[1]


def fetch_county(lat: float, lon: float) -> tuple[str, str]:
    """(two-letter state, 5-digit county FIPS) from the Census geocoder."""
    data = get_json(
        CENSUS_URL,
        {
            "x": lon,
            "y": lat,
            "benchmark": "Public_AR_Current",
            "vintage": "Current_Current",
            "layers": "States,Counties",
            "format": "json",
        },
    )
    geographies = data["result"]["geographies"]
    try:
        return geographies["States"][0]["STUSAB"], geographies["Counties"][0]["GEOID"]
    except (KeyError, IndexError) as error:
        raise ApiError(f"Census has no county at ({lat}, {lon})") from error


def fetch_ndvi(lat: float, lon: float, on: date) -> float | None:
    """Latest MODIS 16-day NDVI composite (0-1) on or before `on`.

    Optional: the training NDVI is a different daily product and agrees only loosely
    with MODIS (10 training fires: correlation was weak), so it is off by default.
    """
    first, last = on - timedelta(days=32), on
    data = get_json(
        MODIS_URL,
        {
            "latitude": lat,
            "longitude": lon,
            "band": "250m_16_days_NDVI",
            "startDate": f"A{first.year}{first.timetuple().tm_yday:03d}",
            "endDate": f"A{last.year}{last.timetuple().tm_yday:03d}",
            "kmAboveBelow": 0,
            "kmLeftRight": 0,
        },
    )
    scale = float(data["scale"])
    values = [(s["calendar_date"], s["data"][0]) for s in data.get("subset", [])]
    values = [(d, v) for d, v in values if v > -3000]  # -3000 is the fill value
    return max(values)[1] * scale if values else None
