"""Online (O(1)) features must equal the batch pipeline's features hour by hour."""
import numpy as np
import pandas as pd

from src.config import FINAL_PARQUET_FILE
from src.online_features import StationState

COLS = ["rain_1h", "rain_3h", "rain_6h", "rain_12h", "rain_24h", "rain_48h", "rain_72h",
        "rain_max_intensity_24h", "rain_intensity_change_1h", "api_decay_85"]


def test_online_matches_batch():
    df = pd.read_parquet(FINAL_PARQUET_FILE, columns=["station", "datetime"] + COLS)
    st = df.groupby("station").size().idxmax()
    g = df[df["station"] == st].sort_values("datetime")
    # first continuous segment only (batch also restarts after outages)
    seg_break = g["datetime"].diff().dt.total_seconds().gt(3600).cumsum()
    g = g[seg_break == seg_break.iloc[0]].head(3000)
    s = StationState()
    out = pd.DataFrame([s.update(t, r) for t, r in zip(g["datetime"], g["rain_1h"])])
    for c in COLS:
        assert np.allclose(out[c].to_numpy(), g[c].to_numpy(), atol=1e-3), c
