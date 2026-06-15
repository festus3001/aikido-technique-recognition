"""Segment a page image into instructional-photo regions, in reading order.

These 1970s halftone scans arrange step photos in rows. Rows are cleanly
separable by a horizontal projection (white bands between rows); within a row the
photos often abut with no white gutter, so a column split only succeeds when a
gutter actually exists. We therefore segment to the reliable unit -- the photo
row -- and split it into cells when gutters are present. Each region is tagged
with its granularity ('photo' when a clean cell, 'row' when a whole row), so the
imprecision is explicit and the keyframe-curation step can see it.

Per-cell splitting of abutting framed photos (via frame-edge detection or the
printed step numbers) is the planned improvement.
"""

from __future__ import annotations

import cv2
import numpy as np

Region = tuple[int, int, int, int, str]  # x, y, w, h, granularity


def _bands(mask: np.ndarray, min_len: int) -> list[tuple[int, int]]:
    out, start = [], None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= min_len:
                out.append((start, i))
            start = None
    if start is not None and len(mask) - start >= min_len:
        out.append((start, len(mask)))
    return out


def detect_photo_regions(img: np.ndarray, min_row_frac: float = 0.08,
                         min_cell_frac: float = 0.10) -> list[Region]:
    """Return ordered (x, y, w, h, granularity) regions for the page's photos."""
    H, W = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    _, b = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    B = (b > 0).astype(np.uint8)

    rows = _bands(B.sum(1) > 0.04 * W, int(min_row_frac * H))  # tall content bands = photo rows
    regions: list[Region] = []
    for y0, y1 in rows:
        strip = B[y0:y1]
        cols = _bands(strip.sum(0) > 0.10 * (y1 - y0), int(min_cell_frac * W))
        if len(cols) >= 2:                       # genuine column gutters -> per-photo cells
            for x0, x1 in cols:
                if B[y0:y1, x0:x1].mean() > 0.08:
                    regions.append((x0, y0, x1 - x0, y1 - y0, "photo"))
        else:                                    # abutting photos -> keep the row as one region
            xs = _bands(strip.sum(0) > 0.02 * (y1 - y0), int(0.2 * W))
            x0, x1 = (xs[0][0], xs[-1][1]) if xs else (0, W)
            regions.append((x0, y0, x1 - x0, y1 - y0, "row"))
    return order_reading(regions)


def order_reading(regions: list[Region]) -> list[Region]:
    """Row-major reading order: group by vertical band, then left to right."""
    if not regions:
        return []
    med_h = sorted(r[3] for r in regions)[len(regions) // 2]
    tol = med_h * 0.6
    rows: list[list[Region]] = []
    for r in sorted(regions, key=lambda r: r[1]):
        for row in rows:
            if abs(row[0][1] - r[1]) <= tol:
                row.append(r)
                break
        else:
            rows.append([r])
    ordered: list[Region] = []
    for row in rows:
        ordered.extend(sorted(row, key=lambda r: r[0]))
    return ordered
