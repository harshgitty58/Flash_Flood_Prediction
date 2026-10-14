"""Label-set contract tests (LABELS_PLAN.md §7). Run: pytest -q tests/test_labels.py"""
import sys
from pathlib import Path

import pandas as pd
import pytest

from src.config import OFFICIAL_UTTARAKHAND_DISTRICTS, PROJECT_ROOT

LAB = PROJECT_ROOT / "data/external/labels"
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))


@pytest.fixture(scope="module")
def events():
    return pd.read_csv(LAB / "labels_2022_2025.csv", parse_dates=["date", "end_date"])


@pytest.fixture(scope="module")
def days():
    return pd.read_csv(LAB / "labels_daily.csv", parse_dates=["date"])


def test_canonical_districts_only(events, days):
    assert set(events["district"]) <= set(OFFICIAL_UTTARAKHAND_DISTRICTS)
    assert set(days["district"]) <= set(OFFICIAL_UTTARAKHAND_DISTRICTS)


def test_dates_in_range_and_ordered(events):
    assert events["date"].min() >= pd.Timestamp("2022-01-01") and events["end_date"].max() <= pd.Timestamp("2025-12-31")
    assert (events["end_date"] >= events["date"]).all()
    assert ((events["end_date"] - events["date"]).dt.days <= 3).all()


def test_no_duplicate_district_days(days, events):
    assert not days.duplicated(["source", "district", "date"]).any()
    # merged events of one district never overlap or touch (they would have been merged)
    for _, g in events.sort_values("date").groupby("district"):
        assert ((g["date"].iloc[1:].to_numpy() - g["end_date"].iloc[:-1].to_numpy()) > pd.Timedelta(days=1)).all()


def test_every_event_is_sourced(events):
    assert events["source_ref"].notna().all() and (events["source_ref"].str.len() > 3).all()
    assert events["date_confidence"].isin(["low", "medium", "high"]).all()


def test_sandrp_parser_finds_entries():
    import build_labels as b
    for year, minimum in ((2022, 20), (2023, 25)):
        p = LAB / f"sandrp/uttarakhand_cloudbursts_{year}.html"
        if not p.exists():
            pytest.skip("SANDRP pages not downloaded")
        ex, un = [], []
        assert len(b.parse_sandrp(p, year, ex, un)) >= minimum


def test_resolver_handles_known_variants():
    import build_labels as b
    for raw, want in (("Rudra Prayag", "Rudraprayag"), ("Udam Singh Nagar", "Udham Singh Nagar"), ("Garhwal", "Pauri Garhwal"),
                      ("Pithoragrah", "Pithoragarh"), ("Tehri", "Tehri Garhwal"), ("Pauri", "Pauri Garhwal"), ("Joshimath", "Chamoli")):
        assert b.resolve(raw) == want, raw


def test_lightning_only_entry_excluded():
    ex = pd.read_csv(LAB / "excluded.csv")
    assert ((ex["district"] == "Uttarkashi") & (ex["date"] == "2022-07-01")).any()
