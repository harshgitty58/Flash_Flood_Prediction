"""Labels — download MHA (Disaster Management Division / NERC) daily flood & heavy-rainfall situation reports.

Source: NDM India portal, public JSON list https://ndmindia.mha.gov.in/ndmi/whatNewSituationdetails?language=en and
PDFs via /ndmi/viewUploadedDocument?uid=<document_slno>. Each daily report lists, per state, the districts affected
in the current spell with a date range (e.g. "Uttarakhand 07-17 03 (Chamoli, Almora and Bageshwar)") and the last-24 h
damage table. Kept: flood / rain titles dated after the IMD inventory ends (2023-08-26) up to 2025-12-31.
Output: data/external/labels/mha_sitreps/<YYYY-MM-DD>_<uid>.pdf + .txt (text layer), index.csv
Run: python scripts/fetch_mha_sitreps.py [--from 2023-08-20] [--to 2025-12-31]
"""
import argparse
import time
from pathlib import Path

import pandas as pd
import requests
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/external/labels/mha_sitreps"
BASE = "https://ndmindia.mha.gov.in/ndmi"
UA = {"User-Agent": "Mozilla/5.0 (PRAHAR course project; polite, 1 req/s)"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", default="2023-08-20")
    ap.add_argument("--to", dest="end", default="2025-12-31")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    lst = pd.DataFrame(requests.get(f"{BASE}/whatNewSituationdetails", params={"language": "en"}, headers=UA, timeout=120).json())
    lst["day"] = pd.to_datetime(lst["date"], format="%d/%m/%Y", errors="coerce")
    keep = lst[lst["day"].between(a.start, a.end) & lst["title"].str.contains("flood|rain", case=False)].sort_values("day")
    print(f"{len(keep)} flood/rain reports {a.start} → {a.end}")
    rows = []
    for _, r in keep.iterrows():
        pdf = OUT / f"{r['day']:%Y-%m-%d}_{r['document_slno']}.pdf"
        if not pdf.exists():
            for k in range(3):
                try:
                    resp = requests.get(f"{BASE}/viewUploadedDocument", params={"uid": r["document_slno"]}, headers=UA, timeout=120)
                    if resp.ok and resp.content[:4] == b"%PDF":
                        pdf.write_bytes(resp.content)
                        break
                except requests.RequestException:
                    pass
                time.sleep(3 * (k + 1))
            time.sleep(1)
        txt = pdf.with_suffix(".txt")
        if pdf.exists() and not txt.exists():
            try:
                txt.write_text("\n".join(p.extract_text() or "" for p in PdfReader(pdf).pages), encoding="utf-8")
            except Exception as e:  # noqa: BLE001
                print("text failed", pdf.name, type(e).__name__)
        rows.append({"day": r["day"].date(), "uid": r["document_slno"], "title": r["title"].strip(), "pdf": pdf.name if pdf.exists() else None,
                     "text_chars": len(txt.read_text(encoding="utf-8")) if txt.exists() else 0})
        if len(rows) % 25 == 0:
            print(f"  {len(rows)}/{len(keep)} {r['day']:%Y-%m-%d}", flush=True)
    pd.DataFrame(rows).to_csv(OUT / "index.csv", index=False)
    ok = sum(1 for x in rows if x["text_chars"] > 500)
    print(f"done: {len(rows)} reports, {ok} with readable text")


if __name__ == "__main__":
    main()
