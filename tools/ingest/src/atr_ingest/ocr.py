"""OCR via tesseract (pytesseract), bilingual Japanese + English.

We use pytesseract rather than shelling to `tesseract ... stdout`, which behaves
badly when piped. image_to_string gives text; image_to_data gives per-word boxes
and confidence, used to locate caption lines on a photo-dominated page.
"""

from __future__ import annotations

import numpy as np
import pytesseract

DEFAULT_LANG = "jpn+eng"


def text_lines(img: np.ndarray, lang: str = DEFAULT_LANG, psm: int = 11) -> list[str]:
    """OCR an image to a list of non-empty text lines (sparse-text mode by default)."""
    raw = pytesseract.image_to_string(img, lang=lang, config=f"--psm {psm}")
    return [ln.strip() for ln in raw.splitlines() if ln.strip()]


def words_with_boxes(img: np.ndarray, lang: str = DEFAULT_LANG, psm: int = 11) -> list[dict]:
    """Return [{text, conf, left, top, width, height, line}] for words with conf >= 0."""
    data = pytesseract.image_to_data(img, lang=lang, config=f"--psm {psm}",
                                     output_type=pytesseract.Output.DICT)
    out = []
    for i, txt in enumerate(data["text"]):
        txt = txt.strip()
        conf = float(data["conf"][i])
        if not txt or conf < 0:
            continue
        out.append({
            "text": txt, "conf": conf,
            "left": data["left"][i], "top": data["top"][i],
            "width": data["width"][i], "height": data["height"][i],
            "line": data.get("line_num", [0] * len(data["text"]))[i],
            "block": data.get("block_num", [0] * len(data["text"]))[i],
            "par": data.get("par_num", [0] * len(data["text"]))[i],
        })
    return out


def region_text(img: np.ndarray, bbox: tuple[int, int, int, int], lang: str = DEFAULT_LANG,
                psm: int = 6) -> str:
    """OCR a single rectangular region (x, y, w, h) as a uniform block."""
    x, y, w, h = bbox
    crop = img[max(0, y):y + h, max(0, x):x + w]
    return pytesseract.image_to_string(crop, lang=lang, config=f"--psm {psm}").strip()
