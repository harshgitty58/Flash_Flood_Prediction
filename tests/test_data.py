"""D4 — data contract tests. Run: pytest -q tests/test_data.py"""
import glob
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.cleaning import parse_cwc_timestamp
from src.config import CLEANED_DIR, FINAL_PARQUET_FILE, PROJECT_ROOT
from src.data_loader import FEATURE_EXPERIMENTS, FINAL_EXPERIMENT
from src.normalization import FeatureNormalizer

TARGET = "flood_event_24h"


@pytest.fixture(scope="module")
def final():
    return pd.read_parquet(FINAL_PARQUET_FILE)


@pytest.fixture(scope="module")
def inventory():
    return pd.read_parquet(CLEANED_DIR / "flood_inventory_cleaned.parquet")


def test_raw_files_match_manifest():
    """The pipeline reads curated_dataset/ (one copy); every raw CSV must match its SHA-256 in MANIFEST.sha256."""
    root = PROJECT_ROOT / "curated_dataset"
    manifest = dict(line.split("  ", 1)[::-1] for line in (root / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines() if line)
    on_disk = {Path(f).relative_to(root).as_posix() for f in glob.glob(str(root / "**" / "*.csv"), recursive=True)}
    assert on_disk == set(manifest), on_disk ^ set(manifest)
    for rel, digest in manifest.items():
        assert hashlib.sha256((root / rel).read_bytes()).hexdigest() == digest, rel


def test_every_timestamp_parses():
    for f in glob.glob(str(PROJECT_ROOT / "curated_dataset/cwc_rainfall_uttarakhand/*.csv")):
        s = pd.read_csv(f, usecols=["Data Acquisition Time"])["Data Acquisition Time"]
        assert parse_cwc_timestamp(s).notna().all(), f"unparsed timestamps in {f}"


def test_parser_handles_single_digit_hours():
    out = parse_cwc_timestamp(pd.Series(["06-10-2022 0.00", "06-10-2022 9.00", "06-10-2022 23.00"]))
    assert list(out.dt.hour) == [0, 9, 23]


def test_no_invalid_rain_survives_cleaning():
    c = pd.read_parquet(CLEANED_DIR / "rainfall_cleaned.parquet")
    valid = c[c["rainfall_quality_flag"] == "valid"]["rainfall_clean"]
    assert valid.max() <= 150 and valid.min() >= 0
    assert c.loc[c["rainfall_raw"] == 511.5, "rainfall_clean"].isna().all()


def test_no_duplicate_station_hours(final):
    assert not final.duplicated(["station", "datetime"]).any()


def test_rain_windows_are_clock_hours(final):
    """rain_24h must equal the sum of rain_1h over the previous 24 clock hours (spot check)."""
    g = final[final["station"] == final["station"].iloc[0]].set_index("datetime").sort_index()
    t = g.index[len(g) // 2]
    expected = g.loc[t - pd.Timedelta(hours=23): t, "rain_1h"].sum()
    assert np.isclose(g.loc[t, "rain_24h"], expected)


def test_labels_inside_inventory_coverage(final, inventory):
    end = inventory["start_datetime"].max().normalize()
    lab = final[final[TARGET].notna()]
    assert lab["datetime"].max() < end
    assert final.loc[final["datetime"] >= end, TARGET].isna().all()


def test_label_marks_flood_day_and_day_before(final, inventory):
    ev = inventory.drop_duplicates(["district", "start_datetime"])
    ev = ev[(ev["start_datetime"] >= "2023-07-01") & (ev["start_datetime"] < "2023-08-20")].iloc[0]
    rows = final[(final["district"] == ev["district"]) & (final["datetime"].dt.normalize() == ev["start_datetime"].normalize())]
    if len(rows):
        assert (rows[TARGET] == 1).all()


def test_every_recent_event_reaches_labels(final, inventory):
    """Label join is by district name: an unmapped spelling (e.g. 'Rudra Prayag') silently drops the event."""
    from src.config import OFFICIAL_UTTARAKHAND_DISTRICTS
    assert not inventory["district"].isin(["Rudra Prayag", "Udam Singh Nagar", "Garhwal (Regional)", "Garhwal"]).any()
    lab = final[final[TARGET].notna()]
    ev = inventory[inventory["district"].isin(OFFICIAL_UTTARAKHAND_DISTRICTS)
                   & (inventory["start_datetime"] >= lab["datetime"].min().normalize())
                   & (inventory["start_datetime"] < lab["datetime"].max().normalize())].drop_duplicates(["district", "start_datetime"])
    lost = []
    for _, e in ev.iterrows():
        rows = lab[(lab["district"] == e["district"]) & (lab["datetime"].dt.normalize() == e["start_datetime"].normalize())]
        if len(rows) and not (rows[TARGET] == 1).all():
            lost.append(f"{e['district']} {e['start_datetime']:%Y-%m-%d}")
    assert not lost, f"events not labelled: {lost}"
    assert final.loc[final["district"] == "Rudraprayag", TARGET].sum() > 0


def test_history_features_use_only_earlier_days(final, inventory):
    """On a flood day the event itself must not yet be counted in the history features."""
    ev = inventory[(inventory["start_datetime"] >= "2023-07-01") & (inventory["start_datetime"] < "2023-08-20")].iloc[0]
    day = final[(final["district"] == ev["district"]) & (final["datetime"].dt.normalize() == ev["start_datetime"].normalize())]
    if len(day):
        assert (day["days_since_last_flood_prior_t"].dropna() >= 1).all()


def test_final_features_present_and_not_drifting(final):
    feats = FEATURE_EXPERIMENTS[FINAL_EXPERIMENT]
    assert set(feats) <= set(final.columns)
    assert "days_since_last_flood_prior_t" not in feats and "latitude" not in feats


def test_normalizer_roundtrip(tmp_path, final):
    feats = FEATURE_EXPERIMENTS[FINAL_EXPERIMENT]
    X = final[final[TARGET].notna()][feats].fillna(0).head(5000)
    n = FeatureNormalizer().fit(X)
    p = tmp_path / "params.json"
    n.to_json(p)
    assert np.allclose(n.transform(X), FeatureNormalizer.from_json(p).transform(X))


def test_splits_recorded_and_disjoint():
    s = json.loads((PROJECT_ROOT / "results/splits.json").read_text())
    assert s["train"]["end"] < s["validation"]["start"] <= s["validation"]["end"] < s["test"]["start"]
    assert all(s[k]["positives"] > 0 for k in ("train", "validation", "test"))
