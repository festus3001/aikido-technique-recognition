"""Render scanned-PDF pages to images via poppler (pdftoppm).

The PDFs are page-image scans with no text layer, so we rasterize each page at a
chosen DPI and hand the image to OCR and to photo segmentation.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np


def page_count(pdf: str | Path) -> int:
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True).stdout
    for line in out.splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    raise RuntimeError(f"could not read page count from {pdf}")


def render_page(pdf: str | Path, page: int, dpi: int = 300) -> np.ndarray:
    """Render one 1-indexed PDF page to a BGR image array."""
    with tempfile.TemporaryDirectory() as td:
        prefix = Path(td) / "page"
        subprocess.run(
            ["pdftoppm", "-r", str(dpi), "-f", str(page), "-l", str(page),
             "-png", "-singlefile", str(pdf), str(prefix)],
            check=True, capture_output=True)
        png = prefix.with_suffix(".png")
        img = cv2.imread(str(png))
    if img is None:
        raise RuntimeError(f"render failed: {pdf} page {page}")
    return img
