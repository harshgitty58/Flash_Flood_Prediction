"""OCR the scanned MHA situation reports (no text layer, mostly 2025) so parse_mha_sitreps.py can read them.

Renders each page at 150 dpi (pypdfium2) and runs RapidOCR (ONNX, CPU). Lines are re-assembled top-to-bottom,
left-to-right; the .txt next to the PDF is replaced. Re-runs skip reports whose .txt already has text.
Run: python scripts/ocr_mha_sitreps.py
"""
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
from rapidocr_onnxruntime import RapidOCR

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/external/labels/mha_sitreps"


def page_text(engine, img: np.ndarray) -> str:
    res, _ = engine(img)
    if not res:
        return ""
    boxes = sorted(((min(p[1] for p in b), min(p[0] for p in b), t) for b, t, _ in res))
    lines, cur, y0 = [], [], None
    for y, x, t in boxes:  # group boxes into rows (same baseline within 12 px)
        if y0 is not None and abs(y - y0) > 12:
            lines.append(" ".join(w for _, w in sorted(cur))); cur = []
        cur.append((x, t)); y0 = y if not cur[:-1] else y0
    lines.append(" ".join(w for _, w in sorted(cur)))
    return "\n".join(lines)


def main():
    engine = RapidOCR()
    todo = [p for p in sorted(SRC.glob("*.pdf")) if not p.with_suffix(".txt").exists() or p.with_suffix(".txt").stat().st_size < 500]
    print(f"{len(todo)} scanned reports to OCR", flush=True)
    for i, pdf in enumerate(todo, 1):
        doc = pdfium.PdfDocument(str(pdf))
        text = "\n".join(page_text(engine, np.array(doc[k].render(scale=150 / 72).to_pil().convert("RGB"))) for k in range(len(doc)))
        pdf.with_suffix(".txt").write_text(text, encoding="utf-8")
        if i % 10 == 0:
            print(f"  {i}/{len(todo)} {pdf.name} ({len(text)} chars)", flush=True)
    print("done")


if __name__ == "__main__":
    main()
