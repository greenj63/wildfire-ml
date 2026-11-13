"""Tests for the API the frontend uses. No network: live data and models are faked."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.app import fires as fire_store
from backend.app import main, predictor
from backend.live import wfigs
from backend.live.wfigs import Fire

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)


def make_fire(name="TEST", lat=45.0, lon=-118.0, acres=100.0, days_ago=2.5):
    return Fire(name, lat, lon, NOW - timedelta(days=days_ago), reported_acres=acres)


def test_spread_so_far_counts_days_like_training():
    # 2.5 days since discovery = the 3rd day, so 300 acres is 100 acres/day
    assert fire_store.spread_so_far(make_fire(acres=300), NOW) == pytest.approx(100)
    # found this morning: day 1
    assert fire_store.spread_so_far(make_fire(acres=5, days_ago=0.1), NOW) == 5
    assert fire_store.spread_so_far(make_fire(acres=None), NOW) is None
    assert fire_store.spread_so_far(make_fire(acres=0), NOW) is None


def test_nearest_fire_within_range_only():
    near = make_fire("NEAR", 45.01, -118.0)  # about 1 km
    far = make_fire("FAR", 46.0, -118.0)  # about 111 km
    found = fire_store.nearest_fire(45.0, -118.0, [far, near])
    assert found[0].name == "NEAR"
    assert found[1] == pytest.approx(1.1, abs=0.1)
    assert fire_store.nearest_fire(45.0, -118.0, [far]) is None


def test_lower_48_bounds():
    assert fire_store.in_lower_48(38.9, -123.3)
    assert not fire_store.in_lower_48(64.0, -150.0)  # Alaska
    assert not fire_store.in_lower_48(10.0, 10.0)


def test_active_fires_are_cached_and_filtered(monkeypatch):
    calls = []

    def fake_fetch():
        calls.append(1)
        return [make_fire("OK"), make_fire("ALASKA", 64.0, -150.0)]

    monkeypatch.setattr(fire_store, "fetch_active_fires", fake_fetch)
    monkeypatch.setattr(fire_store, "_cache", {"fetched": 0.0, "fires": []})
    assert [f.name for f in fire_store.active_fires(now=1000)] == ["OK"]
    fire_store.active_fires(now=1000 + fire_store.CACHE_SECONDS - 1)
    assert len(calls) == 1  # served from the cache
    fire_store.active_fires(now=1000 + fire_store.CACHE_SECONDS + 1)
    assert len(calls) == 2


def test_active_fires_keep_last_list_when_the_service_fails(monkeypatch):
    monkeypatch.setattr(fire_store, "_cache", {"fetched": 0.0, "fires": [make_fire()]})

    def broken():
        raise RuntimeError("down")

    monkeypatch.setattr(fire_store, "fetch_active_fires", broken)
    assert len(fire_store.active_fires(now=10_000)) == 1


def test_wfigs_active_fire_uses_geometry_when_initial_point_missing():
    feature = {
        "attributes": {
            "IncidentName": "X",
            "InitialLatitude": None,
            "InitialLongitude": None,
            "FireDiscoveryDateTime": 1794423651000,
            "IncidentSize": 12.0,
        },
        "geometry": {"x": -105.5, "y": 38.5},
    }
    fire = wfigs._to_fire(feature)
    assert (fire.latitude, fire.longitude) == (38.5, -105.5)
    assert wfigs._to_fire({"attributes": {"FireDiscoveryDateTime": None}}) is None


def test_active_fires_query_pages_through_results(monkeypatch):
    attrs = {"IncidentName": "A", "InitialLatitude": 40.0, "InitialLongitude": -100.0}
    pages = [
        {
            "features": [
                {"attributes": {**attrs, "FireDiscoveryDateTime": 1794423651000}}
            ],
            "exceededTransferLimit": True,
        },
        {
            "features": [
                {"attributes": {**attrs, "FireDiscoveryDateTime": 1794423651000}}
            ]
        },
    ]
    offsets = []

    def fake_get_json(url, params=None, **kwargs):
        offsets.append(params["resultOffset"])
        return pages[len(offsets) - 1]

    monkeypatch.setattr(wfigs, "get_json", fake_get_json)
    assert len(wfigs.fetch_active_fires()) == 2
    assert offsets == [0, 1]


@pytest.fixture
def client(monkeypatch):
    sample = {column: 1.0 for column in main.MODEL_COLUMNS}
    sample |= {"WEATHER_DATE": "2026-11-10", "SCORE_DATE": "2026-11-10"}
    monkeypatch.setattr(main, "build_sample", lambda fire: dict(sample))
    monkeypatch.setattr(
        predictor,
        "predict_all",
        lambda record: [
            {
                "name": "light_gbm",
                "label": "LightGBM",
                "spread_rate": 0.5,
                "status": "ok",
            }
        ],
    )
    monkeypatch.setattr(
        fire_store, "active_fires", lambda: [make_fire("NEARBY", 45.0, -118.0)]
    )
    return TestClient(main.app)


def test_predict_endpoint(client):
    body = client.get("/api/predict", params={"lat": 45.0, "lon": -118.0}).json()
    assert body["primary_model"] == "light_gbm"
    assert body["models"][0]["spread_rate"] == 0.5
    assert body["weather_date"] == body["drought_date"] == "2026-11-10"
    assert body["nearby_fire"]["name"] == "NEARBY"
    assert body["nearby_fire"]["distance_km"] == 0
    assert body["notice"] is None


def test_predict_has_no_nearby_fire_when_none_close(client):
    body = client.get("/api/predict", params={"lat": 35.0, "lon": -100.0}).json()
    assert body["nearby_fire"] is None


def test_predict_rejects_places_outside_the_lower_48(client):
    response = client.get("/api/predict", params={"lat": 64.0, "lon": -150.0})
    assert response.status_code == 400
    assert "continental" in response.json()["detail"]
    assert client.get("/api/predict", params={"lat": "x", "lon": 1}).status_code == 422


def test_predict_warns_when_live_data_is_missing(client, monkeypatch):
    monkeypatch.setattr(
        main,
        "build_sample",
        lambda fire: (
            {c: 1.0 for c in main.MODEL_COLUMNS}
            | {"WEATHER_DATE": None, "SCORE_DATE": "2026-11-10"}
        ),
    )
    body = client.get("/api/predict", params={"lat": 45.0, "lon": -118.0}).json()
    assert "less reliable" in body["notice"]


def test_fires_endpoint(client):
    body = client.get("/api/fires").json()
    assert body["fires"][0]["name"] == "NEARBY"
    assert body["fires"][0]["acres"] == 100.0
    assert "spread_so_far" in body["fires"][0]


def test_predictor_skips_untrained_models(monkeypatch):
    monkeypatch.setattr(predictor, "algorithm_names", lambda: ["light_gbm", "knn"])
    monkeypatch.setattr(predictor, "is_trained", lambda name: name == "light_gbm")

    class FakeModule:
        @staticmethod
        def predict(record):
            return 1.2345

    monkeypatch.setattr(predictor.importlib, "import_module", lambda name: FakeModule)
    results = predictor.predict_all({})
    assert results[0] | {"label": None} == {
        "name": "light_gbm",
        "label": None,
        "spread_rate": 1.23,
        "status": "ok",
    }
    assert results[1]["status"] == "not_trained"
    assert results[1]["spread_rate"] is None


def test_primary_model_is_listed_first():
    names = predictor.algorithm_names()
    assert names[0] == predictor.PRIMARY_MODEL
    assert "_template" not in names
