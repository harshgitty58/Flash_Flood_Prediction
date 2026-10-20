"""Building & infrastructure exposure around every rain gauge (coloured by that gauge's replay hazard).

Buildings: Microsoft Global ML Building Footprints (polygons extracted from satellite imagery by Microsoft's
pretrained deep segmentation model). Rivers/roads/bridges/schools/hospitals: OpenStreetMap via Overpass.

Every building within RADIUS_KM of a hazard centre is classed by OFFICIAL river-setback zones (distance from the
nearest mapped river/stream centreline) crossed with the centre's warning tier (IMD rainfall categories / hybrid tier):
  zone A  <= 50 m    NGT order (Dec 2017, Ganga in hills): no construction within 50 m; = active flood plain
  zone B  50-100 m   NGT regulatory zone 50-100 m; Jal Shakti Technical Guidelines on Flood Plain Zoning (2025):
                     interim 100 m no-development zone from the river edge until flood plains are mapped
  zone C  100-200 m  Uttarakhand High Court (Aug 2013): no construction within 200 m of any river in the state
  outside 200 m      no official river-setback zone → MINIMAL
  class = tier level in zone A, one level lower in B, two lower in C (order follows the official zone hierarchy;
  the one-level step is the only mapping choice made here).
Height above the river (DEM) is reported for information only: the official flood-plain limit is the 1-in-100-year
highest flood level + 1 m (Uttarakhand Flood Plain Zoning Act 2012, NGT OA 477/2022), and HFL maps are not public.
Hazard sources (src): 0 = live gauge at the replay hour; 1 = offline gauge's last report within STALE_DAYS;
2 = district estimate for towns with no gauge (district-day ranking, src/district_pooled.py: top 3 → ALERT, 4-6 → WATCH).
Zone distances are measured to OSM centrelines (river edge maps are incomplete), so wide rivers are slightly under-zoned.

Run after export_frontend_data.py. Downloads are cached in data/external/.
"""
import gzip
import hashlib
import io
import json
import math
import re
import time
import zipfile
from pathlib import Path

import pandas as pd
import numpy as np
import requests
import yaml
from PIL import Image
from shapely.geometry import LineString, Point, shape
from shapely.ops import nearest_points, transform  # noqa: shapely 2.x still supports it
from shapely.strtree import STRtree
import shapely

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "public" / "data"
CACHE = ROOT / "data" / "external"
P = yaml.safe_load((ROOT / "params.yaml").read_text(encoding="utf-8"))  # shared constants (WS-02.1)
RADIUS_KM, H_MAX_M, D_MAX_M, DEM_Z = P["impact"]["radius_km"], 25.0, 500.0, 13
ZONES_M = tuple(P["impact"]["setback_zones_m"])  # official river-setback zones A/B/C (see docstring)
LEVEL_SCORE = tuple(P["impact"]["level_score"])  # representative score per class MINIMAL..CRITICAL (class cut-offs 20/40/60/80)
D_MAX_STREAM_M, GATE_M, STALE_DAYS, TOWN_KM = 200.0, 1500.0, P["impact"]["stale_days"], P["impact"]["town_km"]
# processed first (city centres, then pilgrimage/event sites), so a suburb never claims a capital's circle
SITES = {"Dehradun": (30.3165, 78.0322), "Haridwar": (29.9457, 78.1642), "Rishikesh": (30.0869, 78.2676), "Roorkee": (29.8543, 77.888),
         "Rudrapur": (28.9845, 79.4141), "Kashipur": (29.2104, 78.9619), "Almora": (29.5971, 79.6591), "Pithoragarh": (29.5829, 80.2182),
         "Nainital": (29.3919, 79.4542), "Pauri": (30.1529, 78.7802), "Tehri": (30.39, 78.48), "Bageshwar": (29.8379, 79.7713),
         "Kedarnath": (30.7346, 79.0669), "Badrinath": (30.7433, 79.4938), "Joshimath": (30.555, 79.565), "Dharali": (31.042, 78.79),
         "Mussoorie": (30.4598, 78.0644), "Gangotri": (30.9946, 78.9411), "Yamunotri": (31.014, 78.4604), "Tharali": (30.07, 79.53),
         "Dharchula": (29.847, 80.534), "Munsiyari": (30.067, 80.239), "Gopeshwar": (30.41, 79.32), "Ukhimath": (30.52, 79.22)}
CHUNK = 3  # stations per Overpass query (one big query times out)
NAMED_KEYS = ("amenity", "tourism", "historic", "shop", "healthcare", "office", "leisure", "man_made", "building")  # indexed per-key filters (a key regex is too slow)
PLACE_RANK = {"city": 1, "town": 1, "village": 2, "suburb": 2, "hamlet": 3}
CLASSES = [(80, "CRITICAL", "#e0115f"), (60, "HIGH", "#ff4d2e"), (40, "MODERATE", "#ff9f1c"), (20, "LOW", "#f5d547"), (0, "MINIMAL", "#3ddc97")]
UA = {"User-Agent": "PRAHAR-course-project/1.0 (+https://github.com/harshgitty58/Flash_Flood_Prediction)"}


def strict(o):
    """Recursively replace NaN/inf with None so the output is valid JSON (browsers reject bare NaN)."""
    if isinstance(o, float):
        return None if (o != o or o in (float("inf"), float("-inf"))) else o
    if isinstance(o, dict):
        return {k: strict(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [strict(v) for v in o]
    if hasattr(o, "item"):  # numpy scalar
        return strict(o.item())
    return o


def quadkey(lat, lon, z=9):
    x = int((lon + 180) / 360 * 2**z)
    s = math.sin(math.radians(lat))
    y = int((0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * 2**z)
    return "".join(str((((y >> i) & 1) << 1) | ((x >> i) & 1)) for i in range(z - 1, -1, -1))


def to_m(lat0):  # local equirectangular metres projection around lat0
    k = math.cos(math.radians(lat0))
    return lambda x, y, z=None: (x * 111320 * k, y * 110540)


def cached(name, fetch, attempts=5):
    """Cache-first download with exponential backoff (network/DNS drops killed a 13-minute run before)."""
    p = CACHE / name
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        for k in range(attempts):
            try:
                p.write_bytes(fetch())
                break
            except (requests.RequestException, OSError) as e:
                if k == attempts - 1:
                    raise
                print(f"  retry {k + 1}/{attempts - 1} for {name}: {type(e).__name__}"); time.sleep(2 ** (k + 1))
    return p.read_bytes()


_tiles = {}


def elev(lon, lat):
    n = 2**DEM_Z
    fx = (lon + 180) / 360 * n
    fy = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    x, y = int(fx), int(fy)
    if (x, y) not in _tiles:
        raw = cached(f"dem/{DEM_Z}_{x}_{y}.png", lambda: requests.get(
            f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{DEM_Z}/{x}/{y}.png", timeout=60).content)
        a = np.asarray(Image.open(io.BytesIO(raw)).convert("RGB"), dtype=np.float64)
        _tiles[(x, y)] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
    return float(_tiles[(x, y)][min(255, int((fy - y) * 256)), min(255, int((fx - x) * 256))])


def elev_arr(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """Vectorised DEM lookup: group points by Terrarium tile, index pixels with numpy."""
    n = 2**DEM_Z
    fx = (lon + 180) / 360 * n
    fy = (1 - np.arcsinh(np.tan(np.radians(lat))) / np.pi) / 2 * n
    tx, ty = fx.astype(int), fy.astype(int)
    out = np.empty(len(lon))
    for x, y in set(zip(tx.tolist(), ty.tolist())):
        elev(*((x + 0.5) / n * 360 - 180, math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 0.5) / n))))))  # load tile
        m = (tx == x) & (ty == y)
        px = np.minimum(255, ((fx[m] - x) * 256).astype(int)); py = np.minimum(255, ((fy[m] - y) * 256).astype(int))
        out[m] = _tiles[(x, y)][py, px]
    return out


_FIRST = re.compile(rb'"coordinates":\s*\[\s*\[\s*\[\s*([-\d.eE]+)\s*,\s*([-\d.eE]+)')


def ms_rings(qks, keep):
    """Yield exterior rings of footprints whose first vertex passes keep(lon, lat). A regex on the raw line avoids
    json-parsing the hundreds of thousands of buildings far from any alert station."""
    links = pd.read_csv(io.BytesIO(cached("ms_dataset_links.csv", lambda: requests.get(
        "https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv", timeout=120).content)))
    rows = links[(links.Location == "India") & links.QuadKey.astype(str).isin(qks)]
    for _, r in rows.iterrows():
        raw = cached(f"ms_{r.QuadKey}_{Path(r.Url).name}", lambda: requests.get(r.Url, timeout=600).content)
        for line in gzip.decompress(raw).splitlines():
            m = _FIRST.search(line)
            if m and keep(float(m.group(1)), float(m.group(2))):
                yield json.loads(line)["geometry"]["coordinates"][0]


def ms_buildings(qks):
    links = pd.read_csv(io.BytesIO(cached("ms_dataset_links.csv", lambda: requests.get(
        "https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv", timeout=120).content)))
    rows = links[(links.Location == "India") & links.QuadKey.astype(str).isin(qks)]
    for _, r in rows.iterrows():
        raw = cached(f"ms_{r.QuadKey}_{Path(r.Url).name}", lambda: requests.get(r.Url, timeout=600).content)
        for line in gzip.decompress(raw).decode().splitlines():
            yield shape(json.loads(line)["geometry"])


def _overpass_query(q: str) -> dict:
    key = f"osm_{hashlib.md5(q.encode()).hexdigest()[:10]}.json"

    def fetch():
        for url in ("https://maps.mail.ru/osm/tools/overpass/api/interpreter", "https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"):
            for _ in range(2):
                try:
                    r = requests.post(url, data={"data": q}, headers=UA, timeout=200)
                except requests.RequestException as e:
                    print("overpass", url, type(e).__name__, "retrying"); continue
                if r.ok and r.content.startswith(b"{"):
                    return r.content
                print("overpass", url, r.status_code, "retrying"); time.sleep(5)
        raise RuntimeError("Overpass unavailable")
    return json.loads(cached(key, fetch))


def overpass(stations, light=False):
    """Rivers, roads and named non-place features around every station, CHUNK stations per query (cached per chunk).
    light=True: rivers/streams only (enough to score buildings), for stale-gauge and town areas, which keeps the
    public Overpass mirrors from timing out."""
    seen, out, failed = set(), [], set()
    for i in range(0, len(stations), CHUNK):
        if light:
            arounds = "".join(f"way(around:{s['r_km']*1000:.0f},{s['lat']},{s['lon']})[waterway~\"river|stream\"];" for s in stations[i:i + CHUNK])
        else:
            arounds = "".join(f"way(around:{RADIUS_KM*1000:.0f},{s['lat']},{s['lon']})[waterway~\"river|stream\"];"
                          f"way(around:{RADIUS_KM*1000:.0f},{s['lat']},{s['lon']})[highway~\"motorway|trunk|primary|secondary|tertiary|unclassified|residential\"];"
                          + "".join(f"nwr(around:{RADIUS_KM*1000:.0f},{s['lat']},{s['lon']})[name][{k}];" for k in NAMED_KEYS)
                          for s in stations[i:i + CHUNK])
        try:
            els = _overpass_query(f"[out:json][timeout:180];({arounds});out geom;")["elements"]
        except RuntimeError:
            print("WARN no OSM for", [s["station"] for s in stations[i:i + CHUNK]], "(left as 'data unavailable')")
            failed.update(s["station"] for s in stations[i:i + CHUNK])
            continue
        for e in els:
            if (e["type"], e["id"]) not in seen:
                seen.add((e["type"], e["id"]))
                out.append(e)
    return {"elements": out, "failed": failed}


def places_statewide() -> list:
    """Every named city/town/village/suburb/hamlet node in Uttarakhand (labels for the whole state)."""
    # GeoNames (CC-BY 4.0, download.geonames.org) instead of an Overpass state query, which times out on the
    # public mirrors. Uttarakhand = admin1 "39"; populated places only (feature class P, abandoned PPLQ dropped).
    z = cached("geonames/IN.zip", lambda: requests.get("https://download.geonames.org/export/dump/IN.zip", timeout=600).content)
    cols = ["id", "name", "ascii", "alt", "lat", "lon", "fclass", "fcode", "cc", "cc2", "admin1", "a2", "a3", "a4", "pop", "elev", "dem", "tz", "mod"]
    with zipfile.ZipFile(io.BytesIO(z)) as zf:
        g = pd.read_csv(zf.open("IN.txt"), sep="\t", header=None, names=cols, dtype={"admin1": str}, quoting=3, low_memory=False)
    g = g[(g["admin1"] == "39") & (g["fclass"] == "P") & ~g["fcode"].isin(["PPLQ", "PPLH", "PPLW"])]
    kind = np.where(g["fcode"].str.startswith("PPLA") | (g["pop"] >= 5000), "town", np.where(g["fcode"].isin(["PPLX", "PPLL"]), "hamlet", "village"))
    a2 = pd.read_csv(io.BytesIO(cached("geonames/admin2Codes.txt", lambda: requests.get("https://download.geonames.org/export/dump/admin2Codes.txt", timeout=300).content)),
                     sep="\t", header=None, names=["code", "name", "ascii", "gid"], dtype=str, quoting=3)
    a2 = {c.split(".")[-1]: ("Pauri Garhwal" if n == "Garhwal" else n) for c, n in zip(a2["code"], a2["ascii"]) if c.startswith("IN.39.")}
    return [{"lat": r.lat, "lon": r.lon, "district": a2.get(str(r.a2).split(".")[0].zfill(3)), "tags": {"name": r.ascii or r.name, "place": k}}
            for r, k in zip(g.itertuples(), kind)]


def main():
    snap = json.loads((WEB / "snapshot.json").read_text())
    st = {s["station"]: s for s in json.loads((WEB / "stations.json").read_text()) if s["kind"] == "rain"}
    live = [{**st[s["station"]], **s, "src": 0, "r_km": RADIUS_KM} for s in snap["stations"] if s["station"] in st]
    T = pd.Timestamp(snap["replay_time"]).tz_localize(None) if pd.Timestamp(snap["replay_time"]).tzinfo else pd.Timestamp(snap["replay_time"])
    rp_ = pd.read_csv(ROOT / "results/warning_levels/replay_warning_levels.csv", usecols=["station", "datetime", "p_calibrated", "tier"], parse_dates=["datetime"])
    rp_ = rp_[(rp_["datetime"] <= T) & (rp_["datetime"] > T - pd.Timedelta(days=STALE_DAYS))].sort_values("datetime").groupby("station").tail(1).set_index("station")
    names_live = {s["station"] for s in live}
    stale = [{**v, "station": n, "p": float(rp_.loc[n, "p_calibrated"]), "tier": rp_.loc[n, "tier"], "last": str(rp_.loc[n, "datetime"])[:16],
              "src": 1, "r_km": RADIUS_KM} for n, v in st.items() if n not in names_live and n in rp_.index]
    gauges = live + stale
    gk = lambda la, lo, ss: min(((math.hypot((lo - s["lon"]) * 111.32 * math.cos(math.radians(la)), (la - s["lat"]) * 110.54), s) for s in ss), key=lambda t: t[0])  # noqa: E731
    rank = pd.read_csv(ROOT / "results/model_upgrade/e3_district_scores.csv", parse_dates=["day"])
    rank = rank[rank["day"] == rank.loc[rank["day"] <= T.normalize(), "day"].max()].sort_values("p", ascending=False)
    rank = {d: i + 1 for i, d in enumerate(rank["district"])}
    PL = places_statewide()
    towns = [(n, la, lo) for n, (la, lo) in SITES.items()] + [(t["tags"]["name"], e["lat"], e["lon"]) for e in places_statewide() for t in [e] if t["tags"]["place"] == "town"]
    est, used = [], set()
    for n, la, lo in towns:
        if n in used or gk(la, lo, gauges)[0] <= RADIUS_KM or (est and gk(la, lo, est)[0] <= 1.5 * TOWN_KM):
            continue
        # district from GeoNames admin2 of the nearest gazetteer place (the nearest gauge can sit across a district line)
        dist_name = min(((la - q["lat"]) ** 2 + (lo - q["lon"]) ** 2, q.get("district")) for q in PL if q.get("district"))[1]
        rk = rank.get(dist_name, 99)
        est.append({"station": f"{n} (district estimate)", "lat": la, "lon": lo, "district": dist_name, "rank": rk,
                    "p": 0.0, "tier": "ALERT" if rk <= 3 else ("WATCH" if rk <= 6 else "NORMAL"), "src": 2, "r_km": TOWN_KM})
        used.add(n)
    hot = gauges + est
    lat0 = sum(s["lat"] for s in hot) / len(hot)
    P = to_m(lat0)
    print("centres: live", len(live), "(>= ALERT:", sum(s["tier"] in ("ALERT", "SEVERE", "EXTREME") for s in live), ") stale", len(stale), "district-estimate towns", len(est))

    ov = overpass([s for s in hot if s["src"] == 0])
    ov2 = overpass([s for s in hot if s["src"] != 0], light=True)
    osm = ov["elements"] + [e for e in ov2["elements"] if (e["type"], e["id"]) not in {(x["type"], x["id"]) for x in ov["elements"]}]
    ov["failed"] |= ov2["failed"]
    hot = [s for s in hot if s["station"] not in ov["failed"]]
    centres = [(s, transform(P, Point(s["lon"], s["lat"]))) for s in hot]
    wways = [e for e in osm if e["type"] == "way" and "waterway" in e.get("tags", {})]
    rivers = [transform(P, LineString([(g["lon"], g["lat"]) for g in e["geometry"]])) for e in wways]
    DMAX = np.array([D_MAX_M if e["tags"]["waterway"] == "river" else D_MAX_STREAM_M for e in wways])
    tree = STRtree(rivers)
    print("osm elements:", len(osm), "river/stream ways:", len(rivers))

    qks = {quadkey(s["lat"] + dy, s["lon"] + dx) for s in hot for dy in (-.06, 0, .06) for dx in (-.07, 0, .07)}
    hot_by_src = {v: sum(s["src"] == v for s in hot) for v in (0, 1, 2)}
    k = math.cos(math.radians(lat0))
    unproj = lambda pt: (pt.x / (111320 * k), pt.y / 110540)
    CX = np.array([pc.x for _, pc in centres]); CY = np.array([pc.y for _, pc in centres])
    # station hazard follows the final hybrid tier (ML or IMD rainfall), so building colours agree with station colours
    TIER_HAZARD = {"NORMAL": 0.0, "WATCH": 0.25, "ALERT": 0.5, "SEVERE": 0.75, "EXTREME": 1.0}
    RK = np.array([sc["r_km"] for sc, _ in centres]) * 1000; SRC = np.array([sc["src"] for sc, _ in centres])
    PS = np.array([max(sc["p"] ** 0.5, TIER_HAZARD.get(sc.get("tier"), 0.0)) for sc, _ in centres])
    LV = np.array([["NORMAL", "WATCH", "ALERT", "SEVERE", "EXTREME"].index(sc.get("tier") or "NORMAL") for sc, _ in centres])
    river_arr = np.array(rivers, dtype=object)

    def score_xy(lon: np.ndarray, lat: np.ndarray, batch=50_000):
        """Vectorised exposure score for many points (in batches). Returns (station_idx, score, h, dist_to_river, in_radius)."""
        if len(lon) > batch:
            parts = [score_xy(lon[i:i + batch], lat[i:i + batch], batch) for i in range(0, len(lon), batch)]
            return tuple(np.concatenate([q[n] for q in parts]) for n in range(6))
        X, Y = lon * 111320 * k, lat * 110540
        D = np.hypot(X[:, None] - CX[None, :], Y[:, None] - CY[None, :])
        j = D.argmin(1); inr = D[np.arange(len(X)), j] <= RK[j]
        pts = shapely.points(X, Y)
        (qi, ri), dw = tree.query_nearest(pts, return_distance=True, all_matches=False)
        dist = np.full(len(X), np.inf); dist[qi] = dw
        ridx = np.zeros(len(X), dtype=int); ridx[qi] = ri
        rp = shapely.get_coordinates(shapely.shortest_line(river_arr[ridx], pts))[0::2]  # point on the river
        h = elev_arr(lon, lat) - elev_arr(rp[:, 0] / (111320 * k), rp[:, 1] / 110540)
        zone = np.searchsorted(np.array(ZONES_M), dist, side="left")  # 0 = A (<=50 m), 1 = B, 2 = C, 3 = outside
        level = np.where(zone <= 2, np.clip(LV[j] - zone, 0, 4), 0)
        score = np.array(LEVEL_SCORE)[level]
        return j, score, h, dist, inr, zone

    ll_c = [(sc["lon"], sc["lat"], (sc["r_km"] / 111.0) ** 2) for sc, _ in centres]
    keep = lambda x, y: any((x - cx) ** 2 * k * k + (y - cy) ** 2 <= r2 for cx, cy, r2 in ll_c)  # noqa: E731
    t0 = time.perf_counter()
    rings = list(ms_rings(qks, keep))
    t1 = time.perf_counter()
    feats = []
    if rings and rivers:
        cen = np.array([np.mean(np.asarray(rg)[:-1], axis=0) for rg in rings])
        j, score, h, dist, inr, zone = score_xy(cen[:, 0], cen[:, 1])
        for n_, rg in enumerate(rings):
            if not inr[n_]:
                continue
            a = np.asarray(rg); xs, ys = a[:, 0] * 111320 * k, a[:, 1] * 110540
            area = 0.5 * abs(np.dot(xs, np.roll(ys, 1)) - np.dot(ys, np.roll(xs, 1)))
            feats.append({"type": "Feature",
                          "geometry": {"type": "Polygon", "coordinates": [[[round(x, 5), round(y, 5)] for x, y in rg]]},
                          "properties": {"i": len(feats) + 1, "st": int(j[n_]), "src": int(SRC[j[n_]]), "z": int(zone[n_]), "s": int(score[n_]), "h": round(float(h[n_]), 1),
                                         "d": round(float(dist[n_])), "a": round(float(area))}})
    print(f"footprints read+filtered in {t1 - t0:.1f}s, scored in {time.perf_counter() - t1:.1f}s")
    live_f = [f for f in feats if f["properties"]["src"] == 0]  # KPIs stay live-gauge based (plan guardrail)
    seen = len(live_f)
    by_cls = {n: 0 for _, n, _ in CLASSES}
    for f in live_f:
        by_cls[next(n for cut, n, _ in CLASSES if f["properties"]["s"] >= cut)] += 1
    exposed = sum(f["properties"]["s"] >= 40 for f in live_f)
    by_source = {name: {"centres": hot_by_src[v], "buildings": sum(f["properties"]["src"] == v for f in feats),
                        ">=MODERATE": sum(f["properties"]["src"] == v and f["properties"]["s"] >= 40 for f in feats)}
                 for v, name in ((0, "live_gauge"), (1, "last_gauge_report"), (2, "district_estimate"))}
    print("by source:", by_source)
    print(f"buildings scored: {seen}, >= MODERATE: {exposed}, DEM tiles: {len(_tiles)}")

    def assets(kind_test):
        out = []
        for e in osm:
            t = e.get("tags", {})
            if not kind_test(e, t):
                continue
            ll = e.get("center") or (e["geometry"][len(e["geometry"]) // 2] if "geometry" in e else {"lat": e["lat"], "lon": e["lon"]})
            pt = transform(P, Point(ll["lon"], ll["lat"]))
            dw = pt.distance(rivers[tree.nearest(pt)]) if rivers else 1e9
            if dw <= 150:
                out.append({"name": t.get("name", "unnamed"), "lat": ll["lat"], "lon": ll["lon"], "dist_water_m": round(dw), "type": t.get("amenity") or t.get("highway")})
        return out

    roads = assets(lambda e, t: "highway" in t and t.get("bridge") != "yes")
    bridges = assets(lambda e, t: "highway" in t and t.get("bridge") == "yes")
    schools = assets(lambda e, t: t.get("amenity") == "school")
    health = assets(lambda e, t: t.get("amenity") in ("hospital", "clinic"))

    df = pd.DataFrame([f["properties"] for f in feats])
    df["station"] = df.st.map(lambda i: hot[i]["station"])
    ring0 = [f["geometry"]["coordinates"][0][0] for f in feats]
    df["lon"], df["lat"] = [c[0] for c in ring0], [c[1] for c in ring0]
    ex = df[df["s"] >= 40]
    focus = (ex if len(ex) else df).groupby("station")[["lon", "lat"]].mean().round(5)  # where the frontend flies to
    by_station = df.groupby("station").agg(buildings=("i", "size"), exposed=("s", lambda x: int((x >= 40).sum())),
                                           mean_score=("s", "mean")).round(1).join(focus).reset_index().to_dict("records")
    KIND_KEYS = ("amenity", "tourism", "historic", "shop", "healthcare", "office", "leisure", "place", "man_made", "building")
    marks, seen_names, cand = [], set(), []
    for e in osm:
        t = e.get("tags", {})
        if "name" not in t or "waterway" in t or "highway" in t or "place" in t:
            continue
        if "lat" in e:
            ll = {"lat": e["lat"], "lon": e["lon"]}
        elif e.get("geometry"):
            ll = e["geometry"][len(e["geometry"]) // 2]
        elif "bounds" in e:
            bb = e["bounds"]; ll = {"lat": (bb["minlat"] + bb["maxlat"]) / 2, "lon": (bb["minlon"] + bb["maxlon"]) / 2}
        else:
            continue
        if (t["name"], round(ll["lat"], 3)) in seen_names:
            continue
        seen_names.add((t["name"], round(ll["lat"], 3)))
        cand.append((t, ll))
    if cand:
        lo = np.array([c[1]["lon"] for c in cand]); la = np.array([c[1]["lat"] for c in cand])
        j_, sc_, h_, d_, inr_, _z = score_xy(lo, la)
        for n_, (t, ll) in enumerate(cand):
            if not inr_[n_]:
                continue
            kk = next(k for k in KIND_KEYS if k in t)
            marks.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(ll["lon"], 5), round(ll["lat"], 5)]},
                          "properties": {"name": t.get("name:en", t["name"]), "kind": t[kk] if t[kk] != "yes" else kk,
                                         "place": int(kk == "place"), "st": int(j_[n_]), "s": int(sc_[n_]), "h": round(float(h_[n_]), 1), "d": round(float(d_[n_]))}})
    pl = places_statewide()
    if pl:
        lo = np.array([e["lon"] for e in pl]); la = np.array([e["lat"] for e in pl])
        j_, sc_, h_, d_, inr_, _z = score_xy(lo, la)
        for n_, e in enumerate(pl):
            t = e["tags"]
            extra = {"st": int(j_[n_]), "s": int(sc_[n_]), "h": round(float(h_[n_]), 1), "d": round(float(d_[n_]))} if inr_[n_] else {"s": -1}
            marks.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(e["lon"], 5), round(e["lat"], 5)]},
                          "properties": {"name": t.get("name:en", t["name"]), "kind": t["place"], "place": 1, "rank": PLACE_RANK.get(t["place"], 3), **extra}})
    (WEB / "landmarks.geojson").write_text(json.dumps(strict({"type": "FeatureCollection", "features": marks}), allow_nan=False, separators=(",", ":")), encoding="utf-8")
    print("landmarks:", len(marks), "places:", sum(m["properties"]["place"] for m in marks))
    (ROOT / "results/impact").mkdir(parents=True, exist_ok=True)
    (ROOT / "results/impact/buildings.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":")))
    (WEB / "impact.json").write_text(json.dumps(strict({
        "method": "Buildings classed by official river-setback zones (A <= 50 m NGT no-construction, B 50-100 m NGT regulatory / Jal Shakti 2025 interim no-development, C 100-200 m Uttarakhand High Court 2013) crossed with the hazard tier (IMD rainfall categories / hybrid model): tier level in A, one lower in B, two lower in C, MINIMAL beyond 200 m. Height above river is shown for information only (official flood plain = 1-in-100-yr HFL + 1 m; HFL maps not public).",
        "station_p": [{"station": s["station"], "p": s["p"], "src": s["src"], "tier": s.get("tier"), "last": s.get("last"), "rank": s.get("rank")} for s in hot],
        "by_source": by_source,
        "replay_time": snap["replay_time"], "stations": [s["station"] for s in hot],
        "buildings_in_radius": seen, "buildings_exposed": exposed, "by_class": by_cls, "by_station": by_station,
        "roads": len(roads), "bridges": bridges, "schools": schools, "health": health,
        "sources": ["Microsoft Global ML Building Footprints (ODbL)", "© OpenStreetMap contributors (ODbL)", "GeoNames (CC-BY 4.0)"],
        # where buildings were scanned and scored; the map shows "data unavailable" outside these circles
        "coverage": {"radius_km": RADIUS_KM,
                     "reporting": [{"station": s["station"], "lat": round(s["lat"], 5), "lon": round(s["lon"], 5), "r_km": s["r_km"], "src": s["src"]} for s in hot],
                     "offline": [{"station": n, "lat": round(v["lat"], 5), "lon": round(v["lon"], 5)} for n, v in st.items()
                                 if n not in {s["station"] for s in hot}]},
    }), allow_nan=False, separators=(",", ":")))
    print("by class:", by_cls, "| roads", len(roads), "bridges", len(bridges), "schools", len(schools), "health", len(health))


if __name__ == "__main__":
    main()
