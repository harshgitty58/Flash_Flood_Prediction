"""GPM IMERG V07 Final daily precipitation over Uttarakhand, 2001-2025 (PRAHAR_MASTER_PLAN.md DS-09 / WS-01.4).

Only the Uttarakhand box (lon 77.5-81.1, lat 28.5-31.5; 37 x 31 cells of 0.1 deg) is requested from NASA GES DISC OPeNDAP,
so one day is ~32 KB instead of a global file. Needs a NASA Earthdata login in ~/_netrc with the GES DISC app approved.
Resumable: existing days are skipped. Output: data/external/imerg_daily/<year>/<yyyymmdd>.nc4 (git-ignored).
Run: python scripts/fetch_imerg_daily.py [start_year] [end_year]
Citation: Huffman et al., GPM IMERG Final Precipitation L3 1 day 0.1 degree V07, GES DISC, doi:10.5067/GPM/IMERGDF/DAY/07
"""
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import earthaccess
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/external/imerg_daily"
URL = ("https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGDF.07/{d:%Y}/{d:%m}/"
       "3B-DAY.MS.MRG.3IMERG.{d:%Y%m%d}-S000000-E235959.V07B.nc4.nc4"
       "?precipitation[0:0][2575:2611][1185:1215],precipitation_cnt[0:0][2575:2611][1185:1215],lon[2575:2611],lat[1185:1215],time")


def fetch(session, d: pd.Timestamp) -> str:
    f = OUT / f"{d:%Y}" / f"{d:%Y%m%d}.nc4"
    if f.exists() and f.stat().st_size > 1000:
        return "skip"
    f.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(4):
        try:
            r = session.get(URL.format(d=d), timeout=120)
            if r.status_code == 404:
                return "missing"
            r.raise_for_status()
            f.write_bytes(r.content)
            return "ok"
        except Exception:  # noqa: BLE001
            time.sleep(2 ** attempt)
    return "failed"


def main():
    y0, y1 = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (2001, 2025)
    earthaccess.login(strategy="netrc")
    s = earthaccess.get_requests_https_session()
    days = pd.date_range(f"{y0}-01-01", f"{y1}-12-31", freq="D")
    counts: dict = {}
    with ThreadPoolExecutor(8) as ex:
        for i, res in enumerate(ex.map(lambda d: fetch(s, d), days), 1):
            counts[res] = counts.get(res, 0) + 1
            if i % 365 == 0 or i == len(days):
                print(f"{i}/{len(days)} days {counts}", flush=True)


if __name__ == "__main__":
    main()
