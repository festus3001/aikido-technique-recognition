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


def _ocr_lines(img: np.ndarray, lang: str, psm: int) -> list[dict]:
    """OCR -> one record per text LINE: {text, conf, x0,y0,x1,y1}."""
    data = pytesseract.image_to_data(img, lang=lang, config=f"--psm {psm}",
                                     output_type=pytesseract.Output.DICT)
    lines: dict[tuple, dict] = {}
    for i in range(len(data["text"])):
        txt = data["text"][i].strip()
        conf = float(data["conf"][i])
        if not txt or conf < 0:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        ln = lines.setdefault(key, {"words": [], "confs": [], "x0": 1e9, "y0": 1e9, "x1": 0, "y1": 0})
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        ln["words"].append((data["word_num"][i], txt))
        ln["confs"].append(conf)
        ln["x0"], ln["y0"] = min(ln["x0"], x), min(ln["y0"], y)
        ln["x1"], ln["y1"] = max(ln["x1"], x + w), max(ln["y1"], y + h)
    out = []
    for ln in lines.values():
        ln["words"].sort()
        out.append({"text": " ".join(w for _, w in ln["words"]),
                    "conf": sum(ln["confs"]) / len(ln["confs"]),
                    "x0": ln["x0"], "y0": ln["y0"], "x1": ln["x1"], "y1": ln["y1"]})
    return out


def _columns(lines: list[dict], page_w: int) -> list[list[dict]]:
    """Split lines into columns at large horizontal gaps between line centers."""
    if not lines:
        return []
    ordered = sorted(lines, key=lambda l: (l["x0"] + l["x1"]) / 2)
    cols, prev = [[ordered[0]]], (ordered[0]["x0"] + ordered[0]["x1"]) / 2
    for l in ordered[1:]:
        cx = (l["x0"] + l["x1"]) / 2
        if cx - prev > 0.16 * page_w:        # a wide gutter -> a new column
            cols.append([])
        cols[-1].append(l)
        prev = cx
    return sorted(cols, key=lambda c: min(l["x0"] for l in c))


def extract_text_blocks(img: np.ndarray, lang: str = "jpn+eng", psm: int = 3,
                        min_conf: float = 30.0, min_chars: int = 4) -> list[dict]:
    """Full-page layout -> coherent text passages: {bbox, text, lang, conf}. Lines are grouped
    into columns, then into passages within a column, breaking on a large vertical gap (a photo
    or paragraph break) or a language flip (Japanese vs the book's English). This rejoins prose
    that Tesseract's block segmentation splits across photo-interrupted columns."""
    page_w = img.shape[1]
    out = []
    for col in _columns(_ocr_lines(img, lang, psm), page_w):
        col.sort(key=lambda l: l["y0"])
        heights = sorted(l["y1"] - l["y0"] for l in col)
        mh = heights[len(heights) // 2] if heights else 20
        cur = None
        for l in col:
            ll = _lang(l["text"])
            gap = (l["y0"] - cur["y1"]) if cur else 0
            flip = cur and ll != "other" and cur["lang"] != "other" and ll != cur["lang"]
            if cur is None or gap > 1.8 * mh or flip:
                cur = {"lines": [l], "x0": l["x0"], "y0": l["y0"], "x1": l["x1"], "y1": l["y1"], "lang": ll}
                out.append(cur)
            else:
                cur["lines"].append(l)
                cur["x0"], cur["x1"], cur["y1"] = min(cur["x0"], l["x0"]), max(cur["x1"], l["x1"]), l["y1"]
                if cur["lang"] == "other":
                    cur["lang"] = ll

    blocks = []
    for p in out:
        text = "\n".join(l["text"] for l in p["lines"]).strip()
        conf = sum(c for l in p["lines"] for c in [l["conf"]]) / len(p["lines"])
        if len(re.sub(r"\s+", "", text)) < min_chars or conf < min_conf:
            continue
        blocks.append({"bbox": [int(p["x0"]), int(p["y0"]), int(p["x1"] - p["x0"]), int(p["y1"] - p["y0"])],
                       "text": text, "lang": _lang(text), "conf": round(conf, 1)})
    blocks.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))   # reading order
    return blocks
