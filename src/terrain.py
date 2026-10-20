"""
Terrain and hydrology from a DEM grid (PRAHAR_MASTER_PLAN.md WS-00.2 / WS-04.7): pure numpy, no GIS dependency.

The brief's terrain group: elevation, slope, aspect, terrain ruggedness (TRI), topographic wetness index (TWI),
flow accumulation, stream power index (SPI), plus height above nearest drainage (HAND) for the impact layer.

  z          2-D elevation array (m), row 0 = north, column 0 = west
  dx, dy     cell size in metres (east-west, north-south); for a lon/lat grid use metres_per_cell(lat, step_deg)

Flow routing: Priority-Flood (Barnes, Lehman & Mulla 2014, Computers & Geosciences 62) seeded from the grid edge
with an epsilon fill, so every interior cell keeps a strictly lower way out (pits are routed through, not trapped),
then D8 steepest descent on the filled surface. Direction codes 0-7 = E, SE, S, SW, W, NW, N, NE; 255 = outlet.
"""
import heapq

import numpy as np

DR = (0, 1, 1, 1, 0, -1, -1, -1)
DC = (1, 1, 0, -1, -1, -1, 0, 1)
OUTLET = 255
EPS = 1e-3  # metres added per step when filling a pit


def metres_per_cell(lat_deg: float, step_deg: float) -> tuple[float, float]:
    """(dx, dy) in metres of a lon/lat cell of `step_deg` at latitude `lat_deg`."""
    return step_deg * 111_320 * np.cos(np.radians(lat_deg)), step_deg * 110_540


def fill(z: np.ndarray) -> np.ndarray:
    """Priority-Flood epsilon fill: returns a surface where every interior cell drains to the grid edge."""
    z = np.where(np.isfinite(z), z, np.nanmax(z) + 1).astype("float64")
    H, W = z.shape
    seen = np.zeros((H, W), bool)
    pq: list = []
    for r in range(H):
        for c in (0, W - 1):
            if not seen[r, c]:
                heapq.heappush(pq, (z[r, c], r, c)); seen[r, c] = True
    for c in range(W):
        for r in (0, H - 1):
            if not seen[r, c]:
                heapq.heappush(pq, (z[r, c], r, c)); seen[r, c] = True
    while pq:
        h, r, c = heapq.heappop(pq)
        for k in range(8):
            rr, cc = r + DR[k], c + DC[k]
            if 0 <= rr < H and 0 <= cc < W and not seen[rr, cc]:
                seen[rr, cc] = True
                z[rr, cc] = max(h + EPS, z[rr, cc])
                heapq.heappush(pq, (z[rr, cc], rr, cc))
    return z


def d8(zf: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """D8 steepest-descent direction on a filled surface; edge cells are outlets."""
    H, W = zf.shape
    best = np.zeros((H, W))
    d = np.full((H, W), OUTLET, "uint8")
    for k in range(8):
        nb = np.full((H, W), np.inf)
        r0, r1 = max(0, -DR[k]), H - max(0, DR[k])
        c0, c1 = max(0, -DC[k]), W - max(0, DC[k])
        nb[r0:r1, c0:c1] = zf[r0 + DR[k]:r1 + DR[k], c0 + DC[k]:c1 + DC[k]]
        g = (zf - nb) / np.hypot(dx * DC[k], dy * DR[k])
        better = g > best
        best = np.where(better, g, best)
        d = np.where(better, k, d).astype("uint8")
    d[0, :] = d[-1, :] = d[:, 0] = d[:, -1] = OUTLET
    return d


def _downstream(d: np.ndarray) -> np.ndarray:
    """Flat index of each cell's downstream neighbour (-1 for outlets)."""
    H, W = d.shape
    r, c = np.indices((H, W))
    k = d.astype(int)
    out = k == OUTLET
    kk = np.where(out, 0, k)
    rr = r + np.take(DR, kk)
    cc = c + np.take(DC, kk)
    down = rr * W + cc
    return np.where(out, -1, down).ravel()


def flow_accumulation(zf: np.ndarray, d: np.ndarray) -> np.ndarray:
    """Number of cells draining through each cell (itself included), processed from high to low filled elevation."""
    down = _downstream(d)
    acc = np.ones(zf.size)
    for i in np.argsort(-zf.ravel(), kind="stable"):
        j = down[i]
        if j >= 0:
            acc[j] += acc[i]
    return acc.reshape(zf.shape)


def streams(acc: np.ndarray, cell_area_m2: float, threshold_km2: float = 1.0) -> np.ndarray:
    """Channel cells: contributing area above `threshold_km2`."""
    return acc * cell_area_m2 >= threshold_km2 * 1e6


def hand(z: np.ndarray, zf: np.ndarray, d: np.ndarray, channel: np.ndarray) -> np.ndarray:
    """Height Above Nearest Drainage along the D8 flow path (Rennó et al. 2008): z minus the elevation of the first
    channel cell the flow reaches. Cells whose path leaves the grid without meeting a channel are NaN."""
    down = _downstream(d)
    zr, ch = z.ravel().astype("float64"), channel.ravel()
    base = np.full(z.size, np.nan)
    for i in np.argsort(zf.ravel(), kind="stable"):    # low to high: the downstream cell is always resolved first
        if ch[i]:
            base[i] = zr[i]
        elif down[i] >= 0:
            base[i] = base[down[i]]
    return np.clip(zr - base, 0, None).reshape(z.shape)


def _horn(z: np.ndarray, dx: float, dy: float) -> tuple[np.ndarray, np.ndarray]:
    """Horn (1981) 3x3 gradients dz/dx (east +) and dz/dy (north +)."""
    p = np.pad(z.astype("float64"), 1, mode="edge")
    a, b, c = p[:-2, :-2], p[:-2, 1:-1], p[:-2, 2:]
    d_, f = p[1:-1, :-2], p[1:-1, 2:]
    g, h, i = p[2:, :-2], p[2:, 1:-1], p[2:, 2:]
    gx = ((c + 2 * f + i) - (a + 2 * d_ + g)) / (8 * dx)
    gy = ((a + 2 * b + c) - (g + 2 * h + i)) / (8 * dy)   # row 0 is north, so north minus south
    return gx, gy


def slope_deg(z: np.ndarray, dx: float, dy: float) -> np.ndarray:
    gx, gy = _horn(z, dx, dy)
    return np.degrees(np.arctan(np.hypot(gx, gy)))


def aspect_deg(z: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """Downslope direction, degrees clockwise from north (0 = faces north, 90 = east); NaN on flat cells."""
    gx, gy = _horn(z, dx, dy)
    a = (np.degrees(np.arctan2(-gx, -gy)) + 360) % 360
    return np.where(np.hypot(gx, gy) > 1e-9, a, np.nan)


def tri(z: np.ndarray) -> np.ndarray:
    """Terrain Ruggedness Index (Riley et al. 1999): sqrt of the summed squared differences to the 8 neighbours."""
    p = np.pad(z.astype("float64"), 1, mode="edge")
    H, W = z.shape
    s = sum((p[1 + r:1 + r + H, 1 + c:1 + c + W] - z) ** 2 for r, c in zip(DR, DC))
    return np.sqrt(s)


def twi_spi(acc: np.ndarray, slope: np.ndarray, dx: float, dy: float) -> tuple[np.ndarray, np.ndarray]:
    """Topographic wetness index ln(a / tan b) and stream power index ln(a * tan b), with a = specific catchment
    area (contributing area / contour width, width = mean cell size) and slope floored at 0.1 degree."""
    a = acc * dx * dy / ((dx + dy) / 2)
    tanb = np.tan(np.radians(np.maximum(slope, 0.1)))
    return np.log(a / tanb), np.log(a * tanb)


def terrain_suite(z: np.ndarray, dx: float, dy: float, channel_km2: float = 1.0) -> dict[str, np.ndarray]:
    """Every terrain layer at once (the inputs to WS-04 terrain features and WS-10 HAND)."""
    zf = fill(z)
    d = d8(zf, dx, dy)
    acc = flow_accumulation(zf, d)
    s = slope_deg(z, dx, dy)
    twi, spi = twi_spi(acc, s, dx, dy)
    ch = streams(acc, dx * dy, channel_km2)
    return {"elev_m": z, "slope_deg": s, "aspect_deg": aspect_deg(z, dx, dy), "tri_m": tri(z),
            "upstream_km2": acc * dx * dy / 1e6, "twi": twi, "spi": spi, "channel": ch, "hand_m": hand(z, zf, d, ch),
            "flow_dir": d}
