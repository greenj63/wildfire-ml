"""Tests for the live data code. No network: HTTP calls are replaced with fake data."""

import math
from datetime import UTC, date, datetime

import pytest

from backend.live import gridmet, mapping, usdm, wfigs
from backend.live.terrain import terrain_from_grid


def test_flat_ground_has_no_aspect():
    result = terrain_from_grid([[10.0] * 3] * 3)
    assert result["Slope"] == 0
    assert result["Aspect"] == -1
    assert result["TPI"] == 0
    assert result["TRI"] == 0


def test_terrain_slope_aspect_tpi_tri():
    # Rises 3 m per 30 m cell toward the east, so it faces west (270 degrees)
    grid = [[0.0, 3.0, 6.0]] * 3
    result = terrain_from_grid(grid, cell=30.0)
    assert result["Slope"] == pytest.approx(math.degrees(math.atan(3 / 30)), abs=1e-6)
    assert result["Aspect"] == pytest.approx(270.0)
    assert result["Elevation"] == 3.0
    assert result["TPI"] == pytest.approx(0.0)  # a plane has no relief
    # Riley TRI: neighbor differences from the center are -3, 0, +3 in pairs: 6 x 9
    assert result["TRI"] == pytest.approx(math.sqrt(54))


def test_south_facing_slope():
    # Rises toward the north, so it faces south (180 degrees)
    grid = [[6.0] * 3, [3.0] * 3, [0.0] * 3]
    assert terrain_from_grid(grid)["Aspect"] == pytest.approx(180.0)


def test_percentile_bins_match_training_labels():
    baseline = list(range(100))  # 0..99
    assert gridmet.percentile_bin(-5, baseline) == "<10%"
    assert gridmet.percentile_bin(20, baseline) == "10-30%"
    assert gridmet.percentile_bin(40, baseline) == "30-50%"
    assert gridmet.percentile_bin(60, baseline) == "50-70%"
    assert gridmet.percentile_bin(80, baseline) == "70-90%"
    assert gridmet.percentile_bin(150, baseline) == ">90%"
    assert gridmet.percentile_bin(5, []) is None


def test_percentile_labels_are_readable_by_the_model():
    from shared.experiment import percentile_midpoint

    for _, label in gridmet.PERCENTILE_EDGES:
        assert not math.isnan(percentile_midpoint(label))
    assert percentile_midpoint(">90%") == 95


def test_gridmet_unpacks_scale_offset_and_fill(monkeypatch):
    csv_text = (
        "time,latitude,longitude,tmmx\n"
        "2026-11-08T00:00:00Z,38.5,-119.9,848.0\n"  # 848 * 0.1 + 220 = 304.8 K
        "2026-11-09T00:00:00Z,38.5,-119.9,32767.0\n"  # fill value, dropped
    )
    monkeypatch.setattr(gridmet, "get_text", lambda *a, **k: csv_text)
    series = gridmet._fetch_series(
        "tmmx", 38.5, -119.9, date(2026, 11, 8), date(2026, 11, 9)
    )
    assert series == {date(2026, 11, 8): pytest.approx(304.8)}


def test_fetch_weather_uses_latest_common_day(monkeypatch):
    def fake_series(key, lat, lon, start, end):
        return {date(2026, 11, 8): 1.0, date(2026, 11, 9): 2.0}

    monkeypatch.setattr(gridmet, "_fetch_series", fake_series)
    weather, weather_date = gridmet.fetch_weather(38.5, -119.9, date(2026, 11, 11))
    assert weather_date == date(2026, 11, 9)  # gridMET lags real time
    assert set(weather) == set(gridmet.VARIABLES)


def test_drought_score_is_dsci_over_100():
    row = {"D0": "100.00", "D1": "10.01", "D2": "0", "D3": "0", "D4": "0"}
    assert usdm.drought_score_from_row(row) == pytest.approx(1.1001)


def test_fetch_drought_score_takes_newest_map(monkeypatch):
    text = (
        "MapDate,FIPS,County,State,None,D0,D1,D2,D3,D4\n"
        "20261027,06003,Alpine County,CA,0,100,0,0,0,0\n"
        "20261103,06003,Alpine County,CA,0,100,50,0,0,0\n"
    )
    monkeypatch.setattr(usdm, "get_text", lambda *a, **k: text)
    score, map_date = usdm.fetch_drought_score("06003", date(2026, 11, 11))
    assert score == pytest.approx(1.5)
    assert map_date == date(2026, 11, 3)


def test_owner_and_agency_mapping():
    assert mapping.owner_description("USFWS") == "FWS"
    assert mapping.owner_description("Private") == "PRIVATE"
    assert mapping.owner_description(None) == "MISSING/NOT SPECIFIED"
    assert mapping.reporting_agency("USFS") == "FS"
    assert mapping.reporting_agency("CAL FIRE") == "ST/C&L"
    assert mapping.reporting_agency("INTER") is None
    assert mapping.reporting_agency(None) is None


def test_local_time_conversion():
    # 2026-11-11 19:00 UTC is 11:00 in California (standard time)
    winter = mapping.local_discovery(
        datetime(2026, 11, 11, 19, tzinfo=UTC), -119.9, "CA"
    )
    assert winter == datetime(2026, 11, 11, 11, 0)
    # In July, California is on daylight time
    summer = mapping.local_discovery(datetime(2026, 7, 4, 19, tzinfo=UTC), -119.9, "CA")
    assert summer.hour == 12
    # Arizona never changes its clocks
    arizona = mapping.local_discovery(
        datetime(2026, 7, 4, 19, tzinfo=UTC), -112.0, "AZ"
    )
    assert arizona.hour == 12  # UTC-7 all year


def test_wfigs_fires_are_parsed(monkeypatch):
    attributes = {
        "IncidentName": "TEST",
        "IrwinID": "{ABC}",
        "InitialLatitude": 34.5,
        "InitialLongitude": -118.1,
        "FireDiscoveryDateTime": 1794423651000,
        "POOState": "US-CA",
        "POOFips": "06037",
        "POOLandownerCategory": "Private",
        "POOProtectingAgency": "C&L",
        "DiscoveryAcres": 0.01,
        "IncidentSize": None,
    }
    no_coordinates = {**attributes, "InitialLatitude": None}
    monkeypatch.setattr(
        wfigs,
        "get_json",
        lambda *a, **k: {
            "features": [{"attributes": no_coordinates}, {"attributes": attributes}]
        },
    )
    fires = wfigs.fetch_recent_fires(hours=24, limit=5)
    assert len(fires) == 1  # the record without coordinates is skipped
    assert fires[0].state == "CA"
    assert fires[0].county_fips == "06037"
    assert fires[0].reported_acres == 0.01
    assert fires[0].discovered.tzinfo is not None
