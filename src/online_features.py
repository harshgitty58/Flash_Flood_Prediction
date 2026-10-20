"""
Incremental (online) rainfall features — the latency algorithm behind the backend's /predict.

Batch features recompute every rolling window over the full history (O(n·w) per station). For live use each new
hourly reading should cost O(1):

  rolling sums (3/6/12/24/48/72 h)  one ring buffer of the last 72 hours; each window keeps a running sum —
                                     add the new hour, subtract the hour that falls out of that window
  24 h max intensity                 monotonic deque of (hour_index, value): amortised O(1) push/pop
  1 h intensity change               previous value
  API (decay 0.85)                   recursion  API_t = 0.85 · API_{t-1} + P_t

Missing hours between updates are treated as 0 mm (CWC only logs rainy hours) unless the gap exceeds the
offline limit, in which case the state is reset (gauge was down) — the same rules as src/rainfall_features.py,
so online and batch features match exactly (tests/test_online_features.py).
"""
from collections import deque
from dataclasses import dataclass, field

import pandas as pd

from src.rainfall_features import OFFLINE_GAP_DRY_H, OFFLINE_GAP_MONSOON_H
from src.params import P

WINDOWS = tuple(P["features"]["rain_windows_h"])
DECAY = P["features"]["api_decay_hourly"]


@dataclass
class StationState:
    buf: deque = field(default_factory=lambda: deque(maxlen=72))  # last 72 hourly values, newest at the right
    sums: dict = field(default_factory=lambda: {w: 0.0 for w in WINDOWS})
    maxq: deque = field(default_factory=deque)                    # (hour_index, value), values decreasing
    api: float = 0.0
    prev: float = 0.0
    hour_index: int = -1
    last_time: pd.Timestamp | None = None

    def _push(self, v: float):
        self.hour_index += 1
        n = len(self.buf)
        for w in WINDOWS:  # subtract the value leaving each window (if the window was full)
            if n >= w:
                self.sums[w] -= self.buf[n - w]
            self.sums[w] += v
        self.buf.append(v)
        while self.maxq and self.maxq[-1][1] <= v:
            self.maxq.pop()
        self.maxq.append((self.hour_index, v))
        while self.maxq[0][0] <= self.hour_index - 24:
            self.maxq.popleft()
        self.api = self.api * DECAY + v
        self.change = v - self.prev
        self.prev = v

    def update(self, t: pd.Timestamp, rain_mm: float) -> dict:
        """Advance the state to hour t with the reading at t. Hours skipped since the last update count as 0 mm."""
        t = pd.Timestamp(t).floor("h")
        if self.last_time is not None:
            gap = int((t - self.last_time) / pd.Timedelta(hours=1))
            limit = OFFLINE_GAP_MONSOON_H if t.month in (6, 7, 8, 9) else OFFLINE_GAP_DRY_H
            if gap > limit:
                self.__init__()  # outage: start fresh, as the batch pipeline does
            else:
                for _ in range(max(0, gap - 1)):
                    self._push(0.0)
        self._push(float(rain_mm or 0.0))
        self.last_time = t
        return self.features()

    def features(self) -> dict:
        f = {f"rain_{w}h": round(self.sums[w], 6) for w in WINDOWS}
        f.update({"rain_1h": self.prev, "rain_max_intensity_24h": self.maxq[0][1] if self.maxq else 0.0,
                  "rain_intensity_change_1h": getattr(self, "change", 0.0), "api_decay_85": round(self.api, 6)})
        return f
