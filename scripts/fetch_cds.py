"""ERA5, ERA5-Land and GloFAS over Uttarakhand, 2001-2025 (PRAHAR_MASTER_PLAN.md DS-07, DS-08, DS-12 / WS-01.6-01.7).

  era5      hourly: total + convective precipitation, CAPE, total column water vapour, 2 m temperature and dewpoint,
            surface pressure, 10 m wind (one request per month)
  era5land  hourly: soil water layers 1-4, total precipitation, runoff (total, surface, sub-surface), snow water
            equivalent, snowmelt (one request per month)
  glofas    daily mean river discharge (GloFAS v5, consolidated), from the EWDS store (one request per year)

Area N 31.5, W 77.5, S 28.5, E 81.1. Needs ~/.cdsapirc (CDS token) and the dataset licences accepted on CDS and EWDS.
CDS queues requests, so a full run takes hours to days; it is resumable (existing files are skipped).
Output: data/external/{era5,era5land,glofas}_cds/... (git-ignored).
Run: python scripts/fetch_cds.py all [start_year end_year]   (or one of: era5land, glofas, era5)
Attribution: Contains modified Copernicus Climate Change Service and Copernicus Emergency Management Service information.
"""
import sys
import time
from pathlib import Path

import cdsapi

ROOT = Path(__file__).resolve().parents[1]
AREA = [31.5, 77.5, 28.5, 81.1]
DAYS = [f"{d:02d}" for d in range(1, 32)]
HOURS = [f"{h:02d}:00" for h in range(24)]
DATASETS = {
    "era5": ("reanalysis-era5-single-levels", ["total_precipitation", "convective_precipitation", "convective_available_potential_energy",
             "total_column_water_vapour", "2m_temperature", "2m_dewpoint_temperature", "surface_pressure",
             "10m_u_component_of_wind", "10m_v_component_of_wind"]),
    "era5land": ("reanalysis-era5-land", ["volumetric_soil_water_layer_1", "volumetric_soil_water_layer_2", "volumetric_soil_water_layer_3",
                 "volumetric_soil_water_layer_4", "total_precipitation", "runoff", "surface_runoff", "sub_surface_runoff",
                 "snow_depth_water_equivalent", "snowmelt"]),
}


BUSY = ("maximum number", "rejected", "queued", "403", "429", "temporarily", "timed out", "connection")


def retrieve(client, dataset: str, req: dict, target: Path, tries: int = 40) -> str:
    """One request at a time. A full per-user queue (or a transient error) is retried after a pause, not marked failed."""
    for attempt in range(tries):
        try:
            client.retrieve(dataset, req).download(str(target))
            return "ok"
        except Exception as e:  # noqa: BLE001
            msg = str(e).lower()
            if not any(k in msg for k in BUSY) or attempt == tries - 1:
                return f"FAILED {str(e)[:200]}"
            time.sleep(min(120 * (attempt + 1), 900))
    return "FAILED retries exhausted"


def cds_key() -> str:
    for line in (Path.home() / ".cdsapirc").read_text(encoding="utf-8").splitlines():
        if line.startswith("key:"):
            return line.split(":", 1)[1].strip()
    raise SystemExit("no key in ~/.cdsapirc")


def monthly(name: str, y0: int, y1: int):
    dataset, variables = DATASETS[name]
    out = ROOT / f"data/external/{name}_cds"
    out.mkdir(parents=True, exist_ok=True)
    client = cdsapi.Client(quiet=True)

    def job(ym):
        y, m = ym
        f = out / f"{name}_{y}{m:02d}.nc"
        if f.exists() and f.stat().st_size > 1000:
            return f"{y}-{m:02d} skip"
        # ERA5-Land accumulations (precipitation, runoff, snowmelt) run from 00 UTC, so the 00:00 value of day D+1 is the total
        # for day D, and one daily snapshot is enough for soil water and snow; 00:00 only keeps the request under the CDS cost limit.
        times = ["00:00"] if name == "era5land" else HOURS
        req = {"variable": variables, "year": [str(y)], "month": [f"{m:02d}"], "day": DAYS, "time": times, "area": AREA,
               "data_format": "netcdf", "download_format": "unarchived"}
        if name == "era5":
            req["product_type"] = ["reanalysis"]
        return f"{y}-{m:02d} {retrieve(client, dataset, req, f)}"

    for ym in [(y, m) for y in range(y0, y1 + 1) for m in range(1, 13)]:   # strictly sequential: CDS caps queued jobs per user
        print(name, job(ym), flush=True)


def glofas(y0: int, y1: int):
    out = ROOT / "data/external/glofas_cds"
    out.mkdir(parents=True, exist_ok=True)
    client = cdsapi.Client(url="https://ewds.climate.copernicus.eu/api", key=cds_key(), quiet=True)
    for y in range(y0, y1 + 1):
        f = out / f"glofas_{y}.nc"
        if f.exists() and f.stat().st_size > 1000:
            print("glofas", y, "skip", flush=True)
            continue
        # EWDS request format (checked against /api/retrieve/v1/processes/cems-glofas-historical, Oct 2026)
        req = {"system_version": ["version_5_0"], "hydrological_model": ["lisflood"], "product_type": ["consolidated"],
               "timespan": ["time_mean"], "variable": ["average_river_discharge_in_the_last_24_hours"], "year": [str(y)],
               "month": [f"{m:02d}" for m in range(1, 13)], "day": DAYS, "area": AREA, "data_format": "netcdf",
               "download_format": "unarchived"}
        print("glofas", y, retrieve(client, "cems-glofas-historical", req, f), flush=True)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    y0, y1 = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (2001, 2025)
    for name in (["era5land", "glofas", "era5"] if which == "all" else [which]):   # one dataset after another, one job at a time
        glofas(y0, y1) if name == "glofas" else monthly(name, y0, y1)
