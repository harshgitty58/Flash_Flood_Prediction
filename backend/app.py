"""
PRAHAR API (FastAPI).

  uvicorn backend.app:app --port 8000          (dev: the web app proxies /api → here, see web/vite.config.ts)

Latency design
- everything is loaded once at startup (model, calibration tables, station states, exported JSON) — no disk I/O per request
- JSON payloads are pre-serialised bytes with a content hash ETag → repeat requests return 304 with no body
- GZip for responses > 1 KB; long Cache-Control for immutable building tiles
- /predict uses O(1) incremental features + lookup-table calibration (backend/inference.py)
- every response carries X-Process-Time-ms so latency is measured, not assumed

Security: CORS is an allow-list (params.yaml → api, overridable with PRAHAR_CORS_ORIGINS, comma-separated);
POST /admin/reload needs the header X-Admin-Token equal to the PRAHAR_ADMIN_TOKEN environment variable
(the route is disabled when the variable is not set).
"""
import asyncio
import hashlib
import json
import os
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import pandas as pd
from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field

from backend.inference import Engine
from src.cleaning import MAX_PLAUSIBLE_MM_HR
from src.params import P

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web/public/data"
RESULTS = ROOT / "results"
EXTERNAL = {
    "carto_style": "https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json",
    "carto_glyphs": "https://tiles.basemaps.cartocdn.com/fonts/Montserrat%20Medium/0-255.pbf",
    "esri_imagery": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/8/105/183",
    "esri_labels": "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/8/105/183",
    "aws_terrain_dem": "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/8/183/105.png",
    "opentopomap": "https://a.tile.opentopomap.org/8/183/105.png",
    "overpass_main": "https://overpass-api.de/api/status",
    "overpass_private_coffee": "https://overpass.private.coffee/api/status",
    "ms_footprints_index": "https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv",
    "google_fonts": "https://fonts.googleapis.com/css2?family=Anton&display=swap",
}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    load_all()
    yield


app = FastAPI(title="PRAHAR API", version="1.0", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1000)
CORS_ORIGINS = [o.strip() for o in os.environ.get("PRAHAR_CORS_ORIGINS", ",".join(P["api"]["cors_origins"])).split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_origin_regex=P["api"]["cors_origin_regex"],
                   allow_methods=["GET", "POST"], allow_headers=["*"])

STATE: dict = {}


class Blob:
    """Pre-serialised payload + ETag."""
    def __init__(self, body: bytes, media: str = "application/json"):
        self.body, self.media, self.etag = body, media, '"' + hashlib.md5(body).hexdigest()[:16] + '"'


def _blob(path: Path) -> Blob:
    return Blob(path.read_bytes(), "application/geo+json" if path.suffix == ".geojson" else "application/json")


def load_all():
    t0 = time.perf_counter()
    blobs = {p.stem: _blob(p) for p in DATA.glob("*.json")} | {p.stem: _blob(p) for p in DATA.glob("*.geojson")}
    # metrics: serve the exported, NaN-free web/public/data/metrics.json (the raw results file contained bare NaN,
    # which browsers reject as JSON, so the Metrics page was blank in API mode)
    STATE.update(blobs=blobs, tiles={}, engine=Engine(), loaded_at=time.time())
    STATE["startup_ms"] = round((time.perf_counter() - t0) * 1000, 1)


@app.middleware("http")
async def timing(request: Request, call_next):
    t0 = time.perf_counter()
    resp = await call_next(request)
    resp.headers["X-Process-Time-ms"] = f"{(time.perf_counter() - t0) * 1000:.2f}"
    return resp


def send(blob: Blob, request: Request, cache: str = "no-cache") -> Response:
    if request.headers.get("if-none-match") == blob.etag:
        return Response(status_code=304, headers={"ETag": blob.etag, "Cache-Control": cache})
    return Response(blob.body, media_type=blob.media, headers={"ETag": blob.etag, "Cache-Control": cache})


def blob_or_404(name: str) -> Blob:
    b = STATE["blobs"].get(name)
    if b is None:
        raise HTTPException(404, f"{name} not exported — run scripts/run_all.py")
    return b


# ---------------- health -----------------------------------------------------------------------------------------
@app.get("/health")
def health():
    e = STATE["engine"]
    return {"status": "ok", "startup_ms": STATE["startup_ms"], "model_features": len(e.features),
            "stations": len(e.static), "datasets": sorted(STATE["blobs"]), "loaded_at": STATE["loaded_at"]}


_ext_cache: dict = {}


@app.get("/health/external")
async def health_external():
    """Probe every third-party service the platform depends on (cached 60 s)."""
    if _ext_cache.get("t", 0) > time.time() - 60:
        return _ext_cache["v"]

    async def probe(client, name, url):
        t0 = time.perf_counter()
        try:
            r = await client.get(url, headers={"User-Agent": "PRAHAR-health/1.0", "Range": "bytes=0-2047"})
            ok = r.status_code < 400
            return {"name": name, "ok": ok, "status": r.status_code, "ms": round((time.perf_counter() - t0) * 1000)}
        except Exception as ex:  # noqa: BLE001
            return {"name": name, "ok": False, "status": None, "ms": round((time.perf_counter() - t0) * 1000), "error": type(ex).__name__}

    async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
        res = await asyncio.gather(*(probe(client, n, u) for n, u in EXTERNAL.items()))
    v = {"checked_at": time.time(), "services": res, "ok": sum(r["ok"] for r in res), "total": len(res)}
    _ext_cache.update(t=time.time(), v=v)
    return v


# ---------------- data (1:1 with the static JSON files the frontend already reads) ------------------------------
@app.get("/data/{name}")
def data(name: str, request: Request):
    return send(blob_or_404(name.removesuffix(".json").removesuffix(".geojson")), request)


@app.get("/stations")
def stations(request: Request):
    return send(blob_or_404("stations"), request)


@app.get("/risk/snapshot")
def snapshot(request: Request):
    return send(blob_or_404("snapshot"), request)


@app.get("/risk/timeline")
def timeline(request: Request):
    return send(blob_or_404("timeline"), request)


@app.get("/model/summary")
def model_summary(request: Request):
    return send(blob_or_404("model"), request)


@app.get("/metrics")
def metrics(request: Request):
    return send(blob_or_404("metrics"), request)


@app.get("/events")
def events(request: Request):
    return send(blob_or_404("events"), request)


@app.get("/impact/summary")
def impact_summary(request: Request):
    return send(blob_or_404("impact"), request)


@app.get("/impact/tiles/index")
def tiles_index(request: Request):
    p = DATA / "bld/index.json"
    if not p.exists():
        raise HTTPException(404, "tiles not built — run scripts/build_building_tiles.py")
    return send(STATE["tiles"].setdefault("index", _blob(p)), request)


@app.get("/impact/tiles/{z}/{x}/{y}")
def tile(z: int, x: int, y: int, request: Request):
    key = f"{z}/{x}/{y}"
    if key not in STATE["tiles"]:
        p = DATA / "bld" / str(z) / str(x) / f"{y}.json"
        if not p.exists():
            return Response(b'{"type":"FeatureCollection","features":[]}', media_type="application/geo+json")
        STATE["tiles"][key] = _blob(p)  # LRU not needed: < 100 tiles
    return send(STATE["tiles"][key], request, cache="public, max-age=86400")


@app.get("/landmarks")
def landmarks(request: Request):
    return send(blob_or_404("landmarks"), request)


# ---------------- live inference ---------------------------------------------------------------------------------
class Reading(BaseModel):
    datetime: str
    rain_mm: float = Field(ge=0, le=MAX_PLAUSIBLE_MM_HR)  # same cap as data cleaning (params.yaml → qc)


class PredictIn(BaseModel):
    station: str
    readings: list[Reading] = []
    overrides: dict[str, float] | None = None


@app.post("/predict")
def predict(body: PredictIn):
    e = STATE["engine"]
    try:
        t0 = time.perf_counter()
        out = e.predict(body.station, [r.model_dump() for r in body.readings], body.overrides)
        out["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        return out
    except KeyError:
        raise HTTPException(404, f"unknown or quarantined station {body.station!r}")


@app.post("/predict/scenario")
def scenario(body: PredictIn):
    """What-if: evaluate overrides (e.g. rain_24h=120) without mutating the station's live state."""
    e = STATE["engine"]
    if body.station not in e.static.index:
        raise HTTPException(404, body.station)
    st = e.states.get(body.station) or e.warm_station(body.station)
    row = {**e.static.loc[body.station].to_dict(), **st.features(), **(body.overrides or {}), "station": body.station}
    r = e.score(pd.DataFrame([row])).iloc[0]
    return {k: (v.item() if hasattr(v, "item") else v) for k, v in
            r[["station", "p_calibrated", "confidence", "cp_set_90", "tier", "tier_ml", "tier_rain", "trigger", "rain_24h"]].items()}


@app.post("/admin/reload")
def reload(x_admin_token: str | None = Header(default=None)):
    expected = os.environ.get("PRAHAR_ADMIN_TOKEN")
    if not expected:
        raise HTTPException(403, "admin routes are disabled: set PRAHAR_ADMIN_TOKEN on the server")
    if not x_admin_token or not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(401, "missing or wrong X-Admin-Token")
    load_all()
    return {"reloaded": True, "startup_ms": STATE["startup_ms"]}
