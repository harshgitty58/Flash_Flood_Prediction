"""Generate notebooks/trackB_train_floodseg_colab.ipynb — U-Net flood segmentation on Kuro Siwo (Colab GPU).

Run: python scripts/make_trackb_notebook.py   → open the notebook in Google Colab (Runtime → T4 GPU → Run all).
"""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s))  # noqa: E731
code = lambda s: C.append(nbf.v4.new_code_cell(s))  # noqa: E731

md("""# PRAHAR Space mode — flood segmentation model (Track B AI component)
U-Net (ResNet-34 encoder) trained on **Kuro Siwo** GRD (Bountos et al., NeurIPS 2024, CC BY 4.0) to segment
**flood / permanent water / no water** from one post-event and two pre-event Sentinel-1 images (VV+VH) plus DEM.
The official Kuro Siwo split is used: `train_GRD` events for training, `test_GRD` events (never seen) for testing.

**Colab:** Runtime → Change runtime type → **T4 GPU**, then *Run all*. Data are streamed from Hugging Face (nothing
to download by hand). At the end a `prahar_floodseg.zip` (ONNX model + normalisation + metrics) is downloaded —
put it in the project at `models/space/` and unzip.

Citation: Bountos N.I. et al. (2024) *Kuro Siwo: 33 billion m² under the water. A global multi-temporal satellite
dataset for rapid flood mapping.* NeurIPS Datasets & Benchmarks.""")
code("""!pip -q install webdataset segmentation-models-pytorch onnx
import torch, numpy as np, io, json, time, math, random
print(torch.__version__, 'GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE — switch runtime to GPU')""")
md("## 1. Data: streamed Kuro Siwo shards")
code("""import webdataset as wds
BASE = 'https://huggingface.co/datasets/orion-ai-lab/Kuro-Siwo-Webdataset/resolve/main'
FAST = True   # deadline mode: 2 of 5 training shards (~22 GB), 1 epoch, capped test  (~35-45 min total on a T4)
TRAIN = [f'pipe:curl -s -L {BASE}/train_GRD/shard-{i:05d}.tar' for i in range(2 if FAST else 5)]   # streamed
VAL   = [f'pipe:curl -s -L {BASE}/test_GRD/shard-00000.tar']                       # unseen events
TEST  = [f'pipe:curl -s -L {BASE}/test_GRD/shard-{i:05d}.tar' for i in (1, 2)]
SAR = ['flood_vv', 'flood_vh', 'sec1_vv', 'sec1_vh', 'sec2_vv', 'sec2_vh']   # post, pre-1, pre-2
IGNORE = 255

def to_arrays(s):
    a = {k.split('.')[0]: np.load(io.BytesIO(v))[0] for k, v in s.items() if k.endswith('.npy')}
    with np.errstate(divide='ignore', invalid='ignore'):
        sar = [10 * np.log10(np.clip(a[k], 1e-4, None)) for k in SAR]      # linear backscatter -> dB
    dem = a['dem'] - np.nanmean(a['dem'])                                     # relative relief inside the chip
    x = np.stack(sar + [dem]).astype('float32')
    y = np.rint(np.nan_to_num(a['mask'], nan=IGNORE)).astype('int64')
    y[(y < 0) | (y > 2)] = IGNORE                                             # no-data codes (e.g. 3) -> ignored
    y[(a['valid_mask'] == 0) | ~np.isfinite(x).all(0)] = IGNORE
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    info = json.loads(s['info.json']) if 'info.json' in s else {}
    return x, y, int(info.get('actid', -1))

def stream(urls, shuffle=0):
    ds = wds.WebDataset(urls, shardshuffle=False, handler=wds.warn_and_continue)
    if shuffle: ds = ds.shuffle(shuffle)
    return ds.map(to_arrays, handler=wds.warn_and_continue)

# normalisation statistics from the first 400 training chips (saved with the model)
xs = [x for x, _, _ in __import__('itertools').islice(stream(TRAIN[:1]), 400)]
X = np.stack(xs); MEAN = X.mean((0, 2, 3)).tolist(); STD = (X.std((0, 2, 3)) + 1e-6).tolist()
print('channel mean', np.round(MEAN, 2), '\\nchannel std', np.round(STD, 2))""")
md("## 2. Model, loss, training (AMP)")
code("""import segmentation_models_pytorch as smp, torch.nn as nn
dev = 'cuda'
model = smp.Unet('resnet34', encoder_weights='imagenet', in_channels=7, classes=3).to(dev)
mean_t, std_t = torch.tensor(MEAN, device=dev)[None, :, None, None], torch.tensor(STD, device=dev)[None, :, None, None]
ce = nn.CrossEntropyLoss(weight=torch.tensor([0.4, 1.0, 2.0], device=dev), ignore_index=IGNORE)
dice = smp.losses.DiceLoss('multiclass', ignore_index=IGNORE)
opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
scaler = torch.cuda.amp.GradScaler()
EPOCHS, BS = (1 if FAST else 3), 16

def batches(ds, bs, aug=False):
    xb, yb = [], []
    for x, y, _ in ds:
        if aug:
            k = random.randint(0, 3); x, y = np.rot90(x, k, (1, 2)), np.rot90(y, k)
            if random.random() < .5: x, y = x[:, :, ::-1], y[:, ::-1]
        xb.append(np.ascontiguousarray(x)); yb.append(np.ascontiguousarray(y))
        if len(xb) == bs:
            yield torch.from_numpy(np.stack(xb)), torch.from_numpy(np.stack(yb)); xb, yb = [], []

def confusion(model, ds, limit=None):
    model.eval(); cm = np.zeros((3, 3), np.int64); n = 0
    with torch.no_grad(), torch.autocast('cuda'):
        for xb, yb in batches(ds, 32):
            p = model((xb.to(dev) - mean_t) / std_t).argmax(1).cpu().numpy(); t = yb.numpy(); m = t != IGNORE
            cm += np.bincount(3 * t[m] + p[m], minlength=9).reshape(3, 3); n += len(xb)
            if limit and n >= limit: break
    model.train(); return cm

def scores(cm):
    iou = np.diag(cm) / (cm.sum(0) + cm.sum(1) - np.diag(cm) + 1e-9)
    tp, fp, fn = cm[2, 2], cm[:, 2].sum() - cm[2, 2], cm[2, :].sum() - cm[2, 2]
    p, r = tp / (tp + fp + 1e-9), tp / (tp + fn + 1e-9)
    return {'iou_nowater': round(iou[0], 4), 'iou_permanent': round(iou[1], 4), 'iou_flood': round(iou[2], 4),
            'flood_precision': round(p, 4), 'flood_recall': round(r, 4), 'flood_f1': round(2 * p * r / (p + r + 1e-9), 4), 'miou': round(iou.mean(), 4)}

best, step, t0 = -1, 0, time.time()
for ep in range(EPOCHS):
    for xb, yb in batches(stream(TRAIN, shuffle=1000), BS, aug=True):
        xb, yb = (xb.to(dev) - mean_t) / std_t, yb.to(dev)
        with torch.autocast('cuda'):
            out = model(xb); loss = ce(out, yb) + dice(out, yb)
        opt.zero_grad(set_to_none=True); scaler.scale(loss).backward(); scaler.step(opt); scaler.update(); step += 1
        if step % 200 == 0: print(f'ep {ep} step {step} loss {loss.item():.3f} {time.time() - t0:.0f}s')
    s = scores(confusion(model, stream(VAL), limit=1000 if FAST else 2000)); print('epoch', ep, 'validation (unseen events):', s)
    if s['iou_flood'] > best: best = s['iou_flood']; torch.save(model.state_dict(), 'best.pt')
model.load_state_dict(torch.load('best.pt'))""")
md("## 3. Test on unseen Kuro Siwo events (official test split)")
code("""cm = confusion(model, stream(TEST[:1] if FAST else TEST), limit=3000 if FAST else None); TEST_SCORES = scores(cm)
print(TEST_SCORES); print('confusion (rows = truth: none, permanent, flood):\\n', cm)""")
md("## 4. Export: ONNX + normalisation + metrics → `prahar_floodseg.zip`")
code("""model.eval().cpu()
torch.onnx.export(model, torch.zeros(1, 7, 224, 224), 'floodseg.onnx', opset_version=17, input_names=['x'], output_names=['logits'],
                  dynamic_axes={'x': {0: 'n', 2: 'h', 3: 'w'}, 'logits': {0: 'n', 2: 'h', 3: 'w'}})
meta = {'arch': 'smp.Unet resnet34', 'channels': SAR + ['dem_relative'], 'input': 'S1 backscatter dB (10*log10 linear), DEM minus chip mean',
        'mean': MEAN, 'std': STD, 'classes': ['no_water', 'permanent_water', 'flood'], 'chip': 224,
        'training_data': 'Kuro Siwo GRD train split (Bountos et al. 2024, CC BY 4.0)', 'test_scores_unseen_events': TEST_SCORES,
        'epochs': EPOCHS, 'trained_utc': time.strftime('%Y-%m-%d %H:%M')}
json.dump(meta, open('floodseg_meta.json', 'w'), indent=2)
!zip -q prahar_floodseg.zip floodseg.onnx floodseg_meta.json best.pt
from google.colab import files; files.download('prahar_floodseg.zip')""")

nb = nbf.v4.new_notebook()
nb.cells = C
nb.metadata["accelerator"] = "GPU"
nb.metadata["colab"] = {"provenance": [], "gpuType": "T4"}
out = ROOT / "notebooks/trackB_train_floodseg_colab.ipynb"
nbf.write(nb, out)
print("wrote", out)
