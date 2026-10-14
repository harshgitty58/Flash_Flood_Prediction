"""Phase 2 — pull ERA5 / ERA5-Land hourly reanalysis for every rain gauge via the Open-Meteo archive API (no key).

Variables: precipitation (mm/h), soil_moisture_0_to_7cm, soil_moisture_7_to_28cm (m³/m³).
Output: data/external/era5/<station>.csv (hourly, IST), cached; re-runs only fetch missing stations.
Run: python scripts/fetch_era5.py
"""
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "data/external/era5"
URL = "https://archive-api.open-meteo.com/v1/archive"
VARS = "precipitation,soil_moisture_0_to_7cm,soil_moisture_7_to_28cm"
START, END = "2022-01-01", "2026-09-14"


def fetch(lat, lon, attempts=5):
    params = {"latitude": lat, "longitude": lon, "start_date": START, "end_date": END, "hourly": VARS, "timezone": "Asia/Kolkata"}
    for k in range(attempts):
        try:
            r = requests.get(URL, params=params, timeout=120)
            if r.ok:
                return r.json()
            print(f"  HTTP {r.status_code}: {r.text[:120]}")
        except requests.RequestException as e:
            print(f"  {type(e).__name__}")
        time.sleep(5 * 2 ** k)
    raise RuntimeError("Open-Meteo unavailable")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    st = pd.read_parquet(ROOT / "data/processed/final/uttarakhand_flash_flood_ml_dataset.parquet",
                         columns=["station", "latitude", "longitude"]).drop_duplicates("station")
    for _, s in st.iterrows():
        f = OUT / f"{s.station}.csv"
        if f.exists():
            continue
        j = fetch(s.latitude, s.longitude)
        df = pd.DataFrame(j["hourly"]).rename(columns={"time": "datetime", "precipitation": "era5_precip",
                                                         "soil_moisture_0_to_7cm": "sm_0_7", "soil_moisture_7_to_28cm": "sm_7_28"})
        df["grid_lat"], df["grid_lon"], df["grid_elev"] = j["latitude"], j["longitude"], j.get("elevation")
        df.to_csv(f, index=False)
        print(f"{s.station}: {len(df):,} hours (grid {j['latitude']:.3f},{j['longitude']:.3f}, {j.get('elevation')} m)")
        time.sleep(1.0)  # be polite to the free API
    print("done:", len(list(OUT.glob('*.csv'))), "stations")


if __name__ == "__main__":
    main()
