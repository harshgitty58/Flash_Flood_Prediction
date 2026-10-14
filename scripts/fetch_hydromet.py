"""Phase 2 — pull Uttarakhand state hydromet observations (USDMA, https://sfo.usdma.in, public CSV export).

Twice-daily station reports (08:30 and 17:30 IST): rainfall since the last reading, dry/wet/max/min temperature,
sky condition and weather class. Fetched month by month into data/external/hydromet/raw/YYYY-MM.csv (cached,
re-runs only fetch missing months), then merged into data/external/hydromet/hydromet_observations.csv.
Run: python scripts/fetch_hydromet.py [--from 2022-01] [--to 2026-10]
"""
import argparse
import io
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/external/hydromet"
URL = "https://sfo.usdma.in/reports/weather/export/csv"
UA = {"User-Agent": "Mozilla/5.0 (PRAHAR course project; contact via repo)"}
COLS = {"District": "district", "Installation Point": "station", "Address Location": "address", "Date": "date", "Time": "time",
        "Rain Fall mm": "rain_mm", "Sky Cond.": "sky", "Weather": "weather"}


def month_ranges(start: str, end: str):
    for m in pd.period_range(start, end, freq="M"):
        yield str(m), m.start_time.strftime("%Y-%m-%d"), min(m.end_time, pd.Timestamp.now()).strftime("%Y-%m-%d")


def fetch_month(a: str, b: str, attempts=5) -> bytes:
    params = {"from_date": a, "to_date": b, "search": "", "sort_by": "date", "sort_direction": "asc"}
    for k in range(attempts):
        try:
            r = requests.get(URL, params=params, headers=UA, timeout=180)
            if r.ok:
                return r.content
            print(f"  HTTP {r.status_code}")
        except requests.RequestException as e:
            print(f"  {type(e).__name__}")
        time.sleep(5 * 2 ** k)
    raise RuntimeError(f"hydromet export failed for {a}..{b}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", default="2022-01")
    ap.add_argument("--to", dest="end", default=pd.Timestamp.now().strftime("%Y-%m"))
    a = ap.parse_args()
    raw = OUT / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    for name, d0, d1 in month_ranges(a.start, a.end):
        f = raw / f"{name}.csv"
        if f.exists() and name != pd.Timestamp.now().strftime("%Y-%m"):
            continue
        content = fetch_month(d0, d1)
        f.write_bytes(content)
        n = max(0, content.count(b"\n") - 1)
        print(f"{name}: {n:,} rows")
        time.sleep(1.5)  # polite to a state-government server

    frames = []
    for f in sorted(raw.glob("*.csv")):
        try:
            d = pd.read_csv(io.BytesIO(f.read_bytes()), encoding="latin-1")
        except pd.errors.EmptyDataError:
            continue
        if d.empty:
            continue
        d = d.rename(columns=lambda c: COLS.get(c, c))
        temp = {c: c.split("(")[0].lower() + "_temp_c" for c in d.columns if "(T)" in c}
        frames.append(d.rename(columns=temp))
    if not frames:
        print("no data returned"); return
    obs = pd.concat(frames, ignore_index=True)
    obs["station"] = obs["station"].astype(str).str.strip().str.title()
    obs["district"] = obs["district"].astype(str).str.strip()
    obs["datetime"] = pd.to_datetime(obs["date"] + " " + obs["time"], format="%d-%b-%Y %H:%M:%S", errors="coerce")
    obs = obs.dropna(subset=["datetime"]).drop_duplicates(["station", "datetime"]).sort_values(["station", "datetime"])
    obs.to_csv(OUT / "hydromet_observations.csv", index=False)
    print(f"merged: {len(obs):,} observations, {obs['station'].nunique()} stations, "
          f"{obs['datetime'].min():%Y-%m-%d} → {obs['datetime'].max():%Y-%m-%d}")


if __name__ == "__main__":
    main()
