"""Orchestration: render -> OCR -> caption -> segment -> link -> keyframes -> store."""

from __future__ import annotations

import re
from pathlib import Path

from . import bookmeta as _bookmeta
from . import keyframes as _kf
from . import ocr as _ocr
from . import photos as _photos
from .captions import (Caption, is_caption, is_weapon_caption, merge_bilingual,
                       parse_caption, parse_weapon_caption)
from .link import link_page
from .render import page_count, render_page
from .store import Store
from .structure import section_for

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


def _weapon_caps(lines: list[dict], section) -> list[tuple]:
    """Weapon-section captions: the named/numbered movements on the page. If none are
    found but the page has content, emit one placeholder so its photos are still kept
    (named from the section; the teacher names it in review)."""
    caps = [(parse_weapon_caption(ln["text"]), ln["top"])
            for ln in lines if is_weapon_caption(ln["text"])]
    if caps:
        return caps
    placeholder = Caption(name_romaji="", qualifiers=[],
                          slots={"technique": None, "attack": None, "direction": None, "form": []},
                          name_native=None,
                          raw=f"{section.context} {section.weapon or ''} {section.kind}".strip())
    return [(placeholder, 0)]


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
        section = section_for(book["id"], page)
        if section.kind == "skip":
            continue
        stats["pages_scanned"] += 1
        img = render_page(pdf, page, dpi)
        words = _ocr.words_with_boxes(img, lang=lang, psm=11)
        lines = _group_lines(words)

        if section.is_weapon:
            caps = _weapon_caps(lines, section)
        else:
            caps = []
            for idx, ln in enumerate(lines):
                if is_caption(ln["text"]):
                    cap = parse_caption(ln["text"], native=_native_for(lines, idx))
                    caps.append((cap, ln["top"]))
            caps = merge_bilingual(caps)  # fold same-page romaji + kanji titles into one
        if not caps:
            continue
        stats["pages_with_caption"] += 1

        boxes = _photos.detect_photo_regions(img)
        for seq, (caption, cap_boxes) in enumerate(link_page(caps, boxes), start=1):
            if not cap_boxes:
                continue  # a caption with no photos is almost always prose, not a title
            tech, kfs = _kf.build_records(book, caption, cap_boxes, img, page,
                                          processed_root, retrieved, repo_root=repo_root,
                                          section=section, seq=seq)
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
