"""Terrain algorithms on synthetic DEMs with known answers (src/terrain.py)."""
import numpy as np
import pytest

from src import terrain as t

DX = DY = 30.0


def plane_east(h=12, w=15, drop_per_m=0.1):
    """Plane falling towards the east: z = 1000 - 0.1 * x."""
    x = np.arange(w) * DX
    return np.tile(1000 - drop_per_m * x, (h, 1))


def test_plane_slope_aspect_and_direction():
    z = plane_east()
    s, a = t.slope_deg(z, DX, DY), t.aspect_deg(z, DX, DY)
    assert np.allclose(s[2:-2, 2:-2], np.degrees(np.arctan(0.1)), atol=1e-6)
    assert np.allclose(a[2:-2, 2:-2], 90.0, atol=1e-6)               # faces east
    d = t.d8(t.fill(z), DX, DY)
    assert (d[1:-1, 1:-1] == 0).all()                                  # every interior cell drains east
    assert (d[0] == t.OUTLET).all() and (d[:, -1] == t.OUTLET).all()


def test_flow_accumulation_counts_row_cells():
    z = plane_east()
    zf = t.fill(z)
    acc = t.flow_accumulation(zf, t.d8(zf, DX, DY))
    w = z.shape[1]
    assert (acc[1:-1, -1] == w - 1).all()                              # east edge receives its whole row (minus col 0)
    assert (acc[1:-1, 1] == 1).all()


def test_pit_is_routed_to_the_edge():
    z = plane_east()
    z[6, 7] -= 50                                                      # a deep pit in the middle
    zf = t.fill(z)
    d = t.d8(zf, DX, DY)
    down = t._downstream(d)
    for start in range(z.size):                                        # every path ends at an outlet, no cycles
        i, steps = start, 0
        while down[i] >= 0:
            i, steps = down[i], steps + 1
            assert steps <= z.size
        assert d.ravel()[i] == t.OUTLET


def test_hand_in_a_v_valley():
    h, w, mid = 10, 11, 5
    col = np.abs(np.arange(w) - mid)
    z = 100 + 5.0 * col[None, :] + 1.0 * np.arange(h)[:, None]        # valley along the middle column, falling north
    channel = np.zeros_like(z, bool); channel[:, mid] = True
    zf = t.fill(z)
    hd = t.hand(z, zf, t.d8(zf, DX, DY), channel)
    assert np.allclose(hd[:, mid], 0)
    assert np.allclose(hd[2:-2, mid + 3], 15.0) and np.allclose(hd[2:-2, mid - 2], 10.0)


def test_tri_twi_spi():
    assert np.allclose(t.tri(np.full((5, 5), 7.0)), 0)
    h, w, mid = 12, 13, 6
    z = 100 + 4.0 * np.abs(np.arange(w) - mid)[None, :] + 0.5 * np.arange(h)[:, None]
    out = t.terrain_suite(z, DX, DY, channel_km2=0.005)
    assert out["twi"][h // 2, mid] > out["twi"][h // 2, mid - 4]       # valley floor wetter than the slope
    assert np.isfinite(out["spi"]).all() and out["channel"][:, mid].any()


@pytest.mark.parametrize("lat", [29.0, 31.0])
def test_metres_per_cell(lat):
    dx, dy = t.metres_per_cell(lat, 0.0003)
    assert 28 < dx < 30 and 33 < dy < 34
