"""NIFC WFIGS: newly reported wildfires (location, discovery time, agency, owner)."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from backend.live.http import get_json

SERVICE = (
    "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/"
    "WFIGS_Incident_Locations_Current/FeatureServer/0/query"
)


@dataclass
class Fire:
    """One reported fire. `discovered` is timezone-aware UTC."""

    name: str
    latitude: float
    longitude: float
    discovered: datetime
    irwin_id: str = ""
    state: str | None = None  # two-letter code, e.g. "CA"
    county_fips: str | None = None  # 5 digits, e.g. "06003"
    owner_category: str | None = None  # WFIGS POOLandownerCategory
    protecting_agency: str | None = None  # WFIGS POOProtectingAgency
    reported_acres: float | None = None
    percent_contained: float | None = None


def _clean_state(value) -> str | None:
    """WFIGS writes states as "US-CA"."""
    return value.split("-")[-1] if value else None


OUT_FIELDS = (
    "IncidentName,IrwinID,InitialLatitude,InitialLongitude,FireDiscoveryDateTime,"
    "POOState,POOFips,POOLandownerCategory,POOProtectingAgency,DiscoveryAcres,"
    "IncidentSize,PercentContained"
)
PAGE_SIZE = 1000


def _to_fire(feature: dict) -> Fire | None:
    """A Fire from one ArcGIS feature, or None if it has no usable location or time."""
    a = feature["attributes"]
    lat, lon = a.get("InitialLatitude"), a.get("InitialLongitude")
    geometry = feature.get("geometry") or {}  # some records only have a map point
    if lat is None or lon is None:
        lat, lon = geometry.get("y"), geometry.get("x")
    if lat is None or lon is None or a.get("FireDiscoveryDateTime") is None:
        return None
    return Fire(
        name=a.get("IncidentName") or "UNNAMED",
        latitude=float(lat),
        longitude=float(lon),
        discovered=datetime.fromtimestamp(a["FireDiscoveryDateTime"] / 1000, UTC),
        irwin_id=a.get("IrwinID") or "",
        state=_clean_state(a.get("POOState")),
        county_fips=a.get("POOFips"),
        owner_category=a.get("POOLandownerCategory"),
        protecting_agency=a.get("POOProtectingAgency"),
        reported_acres=a.get("IncidentSize") or a.get("DiscoveryAcres"),
        percent_contained=a.get("PercentContained"),
    )


def fetch_recent_fires(hours: int = 24, limit: int = 5) -> list[Fire]:
    """Wildfires discovered in the last `hours`, newest first."""
    since = datetime.now(UTC) - timedelta(hours=hours)
    data = get_json(
        SERVICE,
        {
            "where": "IncidentTypeCategory='WF' AND "
            f"FireDiscoveryDateTime >= TIMESTAMP '{since:%Y-%m-%d %H:%M:%S}'",
            "outFields": OUT_FIELDS,
            "orderByFields": "FireDiscoveryDateTime DESC",
            "resultRecordCount": limit * 3,  # some records lack coordinates
            "returnGeometry": "false",
            "f": "json",
        },
    )
    fires = [_to_fire(feature) for feature in data.get("features", [])]
    return [fire for fire in fires if fire][:limit]


def fetch_active_fires() -> list[Fire]:
    """Every wildfire that is not out and not fully contained."""
    fires, offset = [], 0
    while True:
        data = get_json(
            SERVICE,
            {
                "where": "IncidentTypeCategory='WF' AND FireOutDateTime IS NULL "
                "AND (PercentContained IS NULL OR PercentContained < 100)",
                "outFields": OUT_FIELDS,
                "orderByFields": "OBJECTID",
                "resultOffset": offset,
                "resultRecordCount": PAGE_SIZE,
                "returnGeometry": "true",
                "outSR": 4326,
                "f": "json",
            },
        )
        features = data.get("features", [])
        fires += [fire for fire in map(_to_fire, features) if fire]
        offset += len(features)
        if not features or not data.get("exceededTransferLimit"):
            return fires
