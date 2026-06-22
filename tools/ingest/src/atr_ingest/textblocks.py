"""Capture every text block on a page: detect, OCR, language-tag, and (for Japanese) translate.

Currently the pipeline keeps only photo captions and discards the instructional prose. That
prose is the teacher's own description of *how* a movement is done -- exactly the material the
deep/qualitative layer needs -- and these books are bilingual, so capturing blocks also keeps
the author's own English. Each block is stored provisional + teacher-correctable.
"""

from __future__ import annotations

import re

import numpy as np
import pytesseract

_CJK = re.compile(r"[぀-ヿ㐀-鿿々]")
_LATIN = re.compile(r"[A-Za-z]")


def _lang(text: str) -> str:
    cjk = len(_CJK.findall(text))
    latin = len(_LATIN.findall(text))
    if cjk and cjk >= latin:
        return "ja"
    if latin and latin > cjk:
        return "en"
    return "ja" if cjk else "other"


def extract_text_blocks(img: np.ndarray, lang: str = "jpn+eng", psm: int = 3,
                        min_conf: float = 30.0, min_chars: int = 4) -> list[dict]:
    """Tesseract full-page layout -> one record per text block: {bbox, text, lang, conf}.
    bbox is [x, y, w, h] in the image's pixel space (render dpi)."""
    data = pytesseract.image_to_data(img, lang=lang, config=f"--psm {psm}",
                                     output_type=pytesseract.Output.DICT)
    blocks: dict[int, dict] = {}
    n = len(data["text"])
    for i in range(n):
        txt = data["text"][i].strip()
        conf = float(data["conf"][i])
        if not txt or conf < 0:
            continue
        b = data["block_num"][i]
        e = blocks.setdefault(b, {"words": [], "confs": [],
                                  "x0": 1e9, "y0": 1e9, "x1": 0, "y1": 0,
                                  "order": []})
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        e["order"].append((data["par_num"][i], data["line_num"][i], data["word_num"][i], txt))
        e["confs"].append(conf)
        e["x0"], e["y0"] = min(e["x0"], x), min(e["y0"], y)
        e["x1"], e["y1"] = max(e["x1"], x + w), max(e["y1"], y + h)

    out = []
    for e in blocks.values():
        e["order"].sort()
        # join words within a line by space, lines by newline (CJK joins tight)
        lines: dict[tuple, list[str]] = {}
        for par, line, _w, txt in e["order"]:
            lines.setdefault((par, line), []).append(txt)
        text = "\n".join(" ".join(ws) for ws in lines.values()).strip()
        plain = re.sub(r"\s+", "", text)
        conf = sum(e["confs"]) / len(e["confs"]) if e["confs"] else 0.0
        if len(plain) < min_chars or conf < min_conf:
            continue
        out.append({"bbox": [int(e["x0"]), int(e["y0"]), int(e["x1"] - e["x0"]), int(e["y1"] - e["y0"])],
                    "text": text, "lang": _lang(text), "conf": round(conf, 1)})
    out.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))   # reading order, top-to-bottom
    return out
