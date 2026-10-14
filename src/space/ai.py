"""Space mode — AI flood segmentation (Track B AI component), CPU inference with ONNX Runtime.

Model: U-Net ResNet-34 trained on Kuro Siwo GRD (Bountos et al. 2024, CC BY 4.0) in Colab
(notebooks/trackB_train_floodseg_colab.ipynb); weights + normalisation in models/space/.
Inputs per pixel (7 channels, as in training): post VV, post VH, pre-1 VV, pre-1 VH, pre-2 VV, pre-2 VH (dB) and
DEM minus the chip mean. Pre-1 / pre-2 are the two last same-orbit acquisitions before the event.
Domain note: training used GRD sigma0; inference uses Planetary Computer RTC gamma0 — a stated limitation.
"""
import json

import numpy as np
import onnxruntime as ort

from src.config import PROJECT_ROOT

MODEL_DIR = PROJECT_ROOT / "models/space"
CHIP = 224


def available() -> bool:
    return (MODEL_DIR / "floodseg.onnx").exists() and (MODEL_DIR / "floodseg_meta.json").exists()


def predict(post: tuple, pre1: tuple, pre2: tuple, dem: np.ndarray) -> np.ndarray:
    """post/pre1/pre2 = (vv_db, vh_db) on the grid. Returns class map (0 no water, 1 permanent, 2 flood, 255 no data)."""
    meta = json.loads((MODEL_DIR / "floodseg_meta.json").read_text())
    sess = ort.InferenceSession(str(MODEL_DIR / "floodseg.onnx"), providers=["CPUExecutionProvider"])
    mean, std = np.array(meta["mean"], "float32")[:, None, None], np.array(meta["std"], "float32")[:, None, None]
    thr = meta.get("flood_threshold")
    stack = np.stack([post[0], post[1], pre1[0], pre1[1], pre2[0], pre2[1], dem]).astype("float32")
    valid = np.isfinite(stack).all(0)
    H, W = dem.shape
    Hp, Wp = -(-H // CHIP) * CHIP, -(-W // CHIP) * CHIP
    pad = np.zeros((7, Hp, Wp), "float32")
    pad[:, :H, :W] = np.nan_to_num(stack)
    out = np.full((Hp, Wp), 255, "uint8")
    chips, where = [], []
    for r in range(0, Hp, CHIP):
        for c in range(0, Wp, CHIP):
            x = pad[:, r:r + CHIP, c:c + CHIP].copy()
            d = x[6]
            x[6] = d - (d[d != 0].mean() if (d != 0).any() else 0)   # DEM relative to the chip mean, as in training
            chips.append((x - mean) / std); where.append((r, c))
    for i in range(0, len(chips), 16):
        logits = sess.run(None, {"x": np.stack(chips[i:i + 16])})[0]
        for (r, c), lg in zip(where[i:i + 16], logits):
            cls = lg.argmax(0)
            if thr is not None:   # flood threshold chosen on the validation split (Colab cell C), not on test
                e = np.exp(lg - lg.max(0)); pf = e[2] / e.sum(0)
                cls = np.where(pf >= thr, 2, np.where(cls == 2, 0, cls))
            out[r:r + CHIP, c:c + CHIP] = cls
    res = out[:H, :W]
    res[~valid] = 255
    return res
