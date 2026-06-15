"""Orchestration: render -> OCR -> caption -> segment -> link -> keyframes -> store."""

from __future__ import annotations

import re
from pathlib import Path

from . import bookmeta as _bookmeta
from . import keyframes as _kf
from . import ocr as _ocr
from . import photos as _photos
from .captions import is_caption, merge_bilingual, parse_caption
from .link import link_page
from .render import page_count, render_page
from .store import Store

_CJK = re.compile(r"[぀-ヿ㐀-鿿　-〿]+")


def _group_lines(words: list[dict]) -> list[dict]:
    """Group OCR words into lines (by block/par/line), preserving position."""
    lines: dict[tuple, list[dict]] = {}
    for w in words:
        lines.setdefault((w["block"], w["par"], w["line"]), []).append(w)
    out = []
    for key, ws in lines.items():
        ws.sort(key=lambda w: w["left"])
        out.append({"text": " ".join(w["text"] for w in ws),
                    "top": min(w["top"] for w in ws),
                    "left": min(w["left"] for w in ws)})
    out.sort(key=lambda l: l["top"])
    return out


def _native_for(lines: list[dict], idx: int) -> str | None:
    """Native (CJK) name for a caption: from the line itself, else the line above."""
    for j in (idx, idx - 1):
        if 0 <= j < len(lines):
            m = _CJK.search(lines[j]["text"])
            if m and len(m.group(0).strip()) >= 2:
                return m.group(0).strip()
    return None


def ingest_book(pdf: Path, book: dict, taxonomy_dir: Path, processed_root: Path,
                repo_root: Path, retrieved: str, pages: list[int] | None = None,
                dpi: int = 300, lang: str = "jpn+eng") -> dict:
    store = Store(taxonomy_dir).load()
    total = page_count(pdf)
    pages = pages or list(range(1, total + 1))
    stats = {"pages_scanned": 0, "pages_with_caption": 0, "techniques": 0, "keyframes": 0}

    for page in pages:
        if page < 1 or page > total:
            continue
        stats["pages_scanned"] += 1
        img = render_page(pdf, page, dpi)
        words = _ocr.words_with_boxes(img, lang=lang, psm=11)
        lines = _group_lines(words)

        caps: list[tuple] = []
        for idx, ln in enumerate(lines):
            if is_caption(ln["text"]):
                cap = parse_caption(ln["text"], native=_native_for(lines, idx))
                caps.append((cap, ln["top"]))
        if not caps:
            continue
        caps = merge_bilingual(caps)  # fold same-page romaji + kanji titles into one record
        stats["pages_with_caption"] += 1

        boxes = _photos.detect_photo_regions(img)
        for caption, cap_boxes in link_page(caps, boxes):
            if not cap_boxes:
                continue  # a caption with no photos is almost always prose, not a title
            tech, kfs = _kf.build_records(book, caption, cap_boxes, img, page,
                                          processed_root, retrieved, repo_root=repo_root)
            store.upsert("techniques", tech)
            store.upsert_many("keyframes", kfs)
            stats["techniques"] += 1
            stats["keyframes"] += len(kfs)

    store.save()

    # Cumulative, book-scoped totals for the description file (not just this run).
    techs = [t for t in store.all("techniques") if t["source"].get("book") == book["id"]]
    kfs = [k for k in store.all("keyframes") if k["source"].get("book") == book["id"]]
    pages_done = sorted({t["source"]["pdf_page"] for t in techs})
    ingested = {"techniques": len(techs), "keyframes": len(kfs),
                "pages_with_content": len(pages_done),
                "page_span": [pages_done[0], pages_done[-1]] if pages_done else None}
    _bookmeta.write_description(book, processed_root, retrieved, ingested=ingested, last_run=stats)
    return stats
