"""API contract tests (in-process, no network except /health/external which is marked)."""
import pytest
from fastapi.testclient import TestClient

from backend.app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health").json()
    assert r["status"] == "ok" and r["stations"] > 30 and r["model_features"] == 23


@pytest.mark.parametrize("path", ["/stations", "/risk/snapshot", "/risk/timeline", "/model/summary", "/metrics",
                                  "/events", "/impact/summary", "/impact/tiles/index", "/landmarks", "/data/snapshot"])
def test_data_endpoints(client, path):
    r = client.get(path)
    assert r.status_code == 200, path
    assert r.headers.get("etag") and float(r.headers["x-process-time-ms"]) < 200


def test_etag_returns_304(client):
    r = client.get("/risk/snapshot")
    assert client.get("/risk/snapshot", headers={"If-None-Match": r.headers["etag"]}).status_code == 304


def test_tiles_listed_exist(client):
    idx = client.get("/impact/tiles/index").json()["tiles"]
    t = idx[0]
    fc = client.get(f"/impact/tiles/{t['z']}/{t['x']}/{t['y']}").json()
    assert len(fc["features"]) == t["n"]


def test_predict_contract_and_latency(client):
    st = client.get("/stations").json()[0]["station"]
    r = client.post("/predict", json={"station": st, "readings": [{"datetime": "2026-09-14 23:00", "rain_mm": 12.5}]})
    assert r.status_code == 200, r.text
    out = r.json()
    assert 0 <= out["p_calibrated"] <= 1 and out["tier"] in {"NORMAL", "WATCH", "ALERT", "SEVERE", "EXTREME"}
    assert out["latency_ms"] < 500  # first call per station warms its state from history
    warm = client.post("/predict", json={"station": st, "readings": [{"datetime": "2026-09-15 00:00", "rain_mm": 1.0}]}).json()
    assert warm["latency_ms"] < 50  # steady-state: O(1) update + lookup calibration


def test_scenario_cloudburst_goes_red(client):
    st = client.get("/stations").json()[0]["station"]
    out = client.post("/predict/scenario", json={"station": st, "overrides": {"rain_1h": 110, "rain_24h": 230}}).json()
    assert out["tier"] in {"SEVERE", "EXTREME"} and out["tier_rain"] in {"SEVERE", "EXTREME"}


def test_unknown_station_404(client):
    assert client.post("/predict", json={"station": "Nowhere", "readings": []}).status_code == 404


@pytest.mark.network
def test_external_services_reachable(client):
    r = client.get("/health/external").json()
    down = [s["name"] for s in r["services"] if not s["ok"]]
    assert r["ok"] >= r["total"] - 2, f"external services down: {down}"


def test_admin_reload_is_protected(client, monkeypatch):
    monkeypatch.delenv("PRAHAR_ADMIN_TOKEN", raising=False)
    assert client.post("/admin/reload").status_code == 403                      # disabled without a server token
    monkeypatch.setenv("PRAHAR_ADMIN_TOKEN", "test-token")
    assert client.post("/admin/reload").status_code == 401                      # no header
    assert client.post("/admin/reload", headers={"X-Admin-Token": "wrong"}).status_code == 401
    assert client.post("/admin/reload", headers={"X-Admin-Token": "test-token"}).status_code == 200


def test_cors_is_an_allow_list(client):
    ok = client.get("/stations", headers={"Origin": "http://localhost:5173"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.get("/stations", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in bad.headers


def test_reading_cap_matches_cleaning():
    from backend.app import Reading
    from src.cleaning import MAX_PLAUSIBLE_MM_HR
    assert Reading.model_fields["rain_mm"].metadata[-1].le == MAX_PLAUSIBLE_MM_HR
