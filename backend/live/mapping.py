"""Translate live source values into the categories and clock the model trained on."""

from datetime import UTC, date, datetime, timedelta

# WFIGS POOLandownerCategory -> training OWNER_DESCR
OWNER_MAP = {
    "USFS": "USFS",
    "BLM": "BLM",
    "BIA": "BIA",
    "NPS": "NPS",
    "USFWS": "FWS",
    "DOD": "OTHER FEDERAL",
    "DOE": "OTHER FEDERAL",
    "Private": "PRIVATE",
    "State": "STATE",
    "County": "COUNTY",
    "City": "MUNICIPAL/LOCAL",
    "OthLoca": "MUNICIPAL/LOCAL",
    "Tribal": "TRIBAL",
}
MISSING_OWNER = "MISSING/NOT SPECIFIED"

# WFIGS POOProtectingAgency -> training NWCG_REPORTING_AGENCY. Everything else (state
# forestry agencies, county and local departments) is "ST/C&L" in the training data.
FEDERAL_AGENCY_MAP = {
    "USFS": "FS",
    "BLM": "BLM",
    "BIA": "BIA",
    "NPS": "NPS",
    "USFWS": "FWS",
    "TRIBE": "TRIBE",
    "USA": "DOD",
}
STATE_LOCAL_AGENCY = "ST/C&L"
UNKNOWN_AGENCIES = {None, "", "INTER"}


def owner_description(wfigs_category: str | None) -> str:
    return OWNER_MAP.get(wfigs_category, MISSING_OWNER)


def reporting_agency(wfigs_agency: str | None) -> str | None:
    """None when the agency is unknown (the model treats that as "missing")."""
    if wfigs_agency in UNKNOWN_AGENCIES:
        return None
    return FEDERAL_AGENCY_MAP.get(wfigs_agency, STATE_LOCAL_AGENCY)


def _nth_sunday(year: int, month: int, n: int) -> date:
    first = date(year, month, 1)
    first_sunday = first + timedelta(days=(6 - first.weekday()) % 7)
    return first_sunday + timedelta(weeks=n - 1)


def utc_offset_hours(longitude: float, state: str | None, when_utc: datetime) -> int:
    """Approximate local UTC offset for the lower 48 (by longitude, US daylight time).

    The model only uses the discovery hour, so an hour of error at a time zone
    border is acceptable.
    """
    if longitude > -85.5:
        standard = -5
    elif longitude > -101:
        standard = -6
    elif longitude > -114:
        standard = -7
    else:
        standard = -8
    if state == "AZ":  # Arizona does not observe daylight time
        return -7
    day = (when_utc + timedelta(hours=standard)).date()
    dst_start = _nth_sunday(day.year, 3, 2)
    dst_end = _nth_sunday(day.year, 11, 1)
    return standard + 1 if dst_start <= day < dst_end else standard


def local_discovery(
    when_utc: datetime, longitude: float, state: str | None
) -> datetime:
    """The discovery moment on the fire's local clock (naive datetime)."""
    when_utc = when_utc.astimezone(UTC)
    return (
        when_utc + timedelta(hours=utc_offset_hours(longitude, state, when_utc))
    ).replace(tzinfo=None)
