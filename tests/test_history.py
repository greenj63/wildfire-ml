"""Tests for fire history (acres and spread rate over time). No network."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.live import history
from backend.live.http import ApiError

GUID = "{548A8D28-1A04-48EE-9011-ABA023175D43}"


def ms(day, hour=12):
    return int(datetime(2026, 7, day, hour, tzinfo=UTC).timestamp() * 1000)


def rec(day, acres, hour=12, **extra):
    return {"poly_PolygonDateTime": ms(day, hour), "poly_GISAcres": acres, **extra}


def test_series_is_one_point_per_day_with_rates():
    series = history.build_series(
        [rec(1, 100), rec(1, 150, hour=20), rec(2, 400), rec(4, 1000)]
    )
    assert [p["date"] for p in series] == ["2026-07-01", "2026-07-02", "2026-07-04"]
    assert [p["acres"] for p in series] == [150, 400, 1000]  # biggest map of the day
    assert [p["rate"] for p in series] == [None, 250, 300]  # 600 acres over 2 days


def test_series_never_shrinks_and_skips_bad_records():
    series = history.build_series(
        [
            rec(1, 500),
            rec(2, 300),  # a later, smaller map is a remap
            rec(3, 900, poly_DeleteThis="Yes - Editing Mistake"),
            rec(3, 900, poly_FeatureCategory="Prescribed Fire"),
            rec(3, None),
            {"poly_GISAcres": 50},  # no date at all
            rec(4, 800, poly_FeatureCategory="Wildfire Daily Fire Perimeter"),
        ]
    )
    assert [p["acres"] for p in series] == [500, 500, 800]
    assert all(p["rate"] is None or p["rate"] >= 0 for p in series)


def test_series_falls_back_to_other_dates():
    only_created = {"poly_CreateDate": ms(5), "poly_GISAcres": 10}
    assert history.build_series([only_created])[0]["date"] == "2026-07-05"


def test_irwin_ids_are_validated():
    assert history.normalize_irwin_id(GUID.lower()) == GUID
    assert history.normalize_irwin_id(GUID.strip("{}")) == GUID
    assert history.normalize_irwin_id("x' OR 1=1 --") is None
    assert history.normalize_irwin_id("") is None


def test_history_needs_two_days_and_is_cached(monkeypatch):
    monkeypatch.setattr(history, "_cache", {})
    calls = []

    def fake_get_json(url, params=None, **kwargs):
        calls.append(params["where"])
        return {"features": [{"attributes": rec(1, 100)}]}

    monkeypatch.setattr(history, "get_json", fake_get_json)
    assert history.fetch_history(GUID, now=0) == []  # one day is not a history
    history.fetch_history(GUID, now=10)
    assert len(calls) == 1
    assert GUID in calls[0]
    history.fetch_history(GUID, now=history.CACHE_SECONDS + 1)
    assert len(calls) == 2


def test_history_rejects_an_unexpected_response(monkeypatch):
    monkeypatch.setattr(history, "_cache", {})
    monkeypatch.setattr(history, "get_json", lambda *a, **k: {})
    with pytest.raises(ApiError):
        history.fetch_history(GUID)


def test_history_endpoint(monkeypatch):
    series = [
        {"date": "2026-07-01", "acres": 10.0, "rate": None},
        {"date": "2026-07-02", "acres": 30.0, "rate": 20.0},
    ]
    monkeypatch.setattr(history, "fetch_history", lambda guid: series)
    client = TestClient(main.app)
    body = client.get("/api/fires/history", params={"irwin_id": GUID}).json()
    assert body == {"irwin_id": GUID, "series": series}
    assert (
        client.get("/api/fires/history", params={"irwin_id": "nope"}).status_code == 400
    )
    assert client.get("/api/fires/history").status_code == 422


def test_history_endpoint_reports_upstream_failure(monkeypatch):
    def broken(guid):
        raise ApiError("down")

    monkeypatch.setattr(history, "fetch_history", broken)
    response = TestClient(main.app).get("/api/fires/history", params={"irwin_id": GUID})
    assert response.status_code == 502
