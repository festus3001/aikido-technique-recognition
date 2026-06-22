"""Orchestration: render -> OCR -> caption -> segment -> link -> keyframes -> store.

The per-page work is `parse_page`, used both by the batch `ingest_book` (write_keyframes=True)
and the review tool's live re-parse (write_keyframes=False, preview). Interpretation is resolved
through the Refinement cascade (schema/refinement.py): the section, any region ops, a forced
caption, and an explicit link can all be refined per scope; code defaults are the base layer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import bookmeta as _bookmeta
from . import captions as _captions
from . import keyframes as _kf
from . import ocr as _ocr
from . import photos as _photos
from .captions import (Caption, is_caption, is_weapon_caption, merge_bilingual,
                       parse_caption, parse_weapon_caption)
from .link import link_page
from .photos import order_reading
from .render import page_count, render_page
from .store import Store
from .structure import Section, section_for

_CJK = re.compile(r"[぀-ヿ㐀-鿿　-〿]+")


@dataclass
class PageParse:
    techniques: list[dict] = field(default_factory=list)
    keyframes: list[dict] = field(default_factory=list)
    section: Section | None = None
    regions: list = field(default_factory=list)        # effective photo regions (post-override)
    captions: list[dict] = field(default_factory=list)  # diagnostics for the UI
    page_size: tuple[int, int] = (0, 0)                # (W, H) for bbox-overlay scaling
    crops: list[np.ndarray] | None = None              # preview only: parallel to keyframes


def _group_lines(words: list[dict]) -> list[dict]:
    """Group OCR words into lines (by block/par/line), preserving position."""
    lines: dict[tuple, list[dict]] = {}
    for w in words:
        lines.setdefault((w["block"], w["par"], w["line"]), []).append(w)
    out = []
    for ws in lines.values():
        ws.sort(key=lambda w: w["left"])
        out.append({"text": " ".join(w["text"] for w in ws),
                    "top": min(w["top"] for w in ws),
                    "left": min(w["left"] for w in ws)})
    out.sort(key=lambda l: l["top"])
    return out


def _weapon_caps(lines: list[dict], section) -> list[tuple]:
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
    for j in (idx, idx - 1):
        if 0 <= j < len(lines):
            m = _CJK.search(lines[j]["text"])
            if m and len(m.group(0).strip()) >= 2:
                return m.group(0).strip()
    return None


# -- override appliers (Refinement-driven; no-op when the store has none) --------
def _apply_region_ops(regions: list, book_id: str, page: int, store) -> list:
    if store is None:
        return regions
    from schema.refinement import resolve
    ops = resolve("region.ops", {"book": book_id, "page": page}, store, base=[])
    for op in ops:
        kind = op.get("op")
        if kind == "manual":
            regions = [tuple(b) + ("photo",) if len(b) == 4 else tuple(b) for b in op.get("boxes", [])]
        elif kind == "drop":
            drop = set(op.get("indices", []))
            regions = [r for i, r in enumerate(regions) if i not in drop]
        elif kind == "merge":
            idx = sorted(op.get("indices", []))
            if len(idx) >= 2 and idx[-1] < len(regions):
                xs = [regions[i] for i in idx]
                x0 = min(r[0] for r in xs); y0 = min(r[1] for r in xs)
                x1 = max(r[0] + r[2] for r in xs); y1 = max(r[1] + r[3] for r in xs)
                merged = (x0, y0, x1 - x0, y1 - y0, "row")
                keep = [r for i, r in enumerate(regions) if i not in set(idx)]
                regions = keep + [merged]
        elif kind == "order":
            if op.get("order") == "column":
                regions = sorted(regions, key=lambda r: (r[0], r[1]))
            else:
                regions = order_reading(regions)
    return regions


def _apply_caption_override(caps: list, book_id: str, page: int, store) -> list:
    if store is None:
        return caps
    from schema.refinement import resolve
    ov = resolve("caption", {"book": book_id, "page": page}, store, base=None)
    if not ov:
        return caps
    forced = Caption(name_romaji=ov.get("name_romaji", ""),
                     qualifiers=ov.get("qualifiers", []),
                     slots=ov.get("slots") or {"technique": None, "attack": None,
                                               "direction": None, "form": []},
                     name_native=ov.get("name_native"),
                     raw=ov.get("name_romaji") or ov.get("name_native") or "")
    if ov.get("suppress_detection", True):
        return [(forced, 0)]
    return caps + [(forced, 0)]


def _apply_link(caps: list, regions: list, book_id: str, page: int, store) -> list:
    if store is not None:
        from schema.refinement import resolve
        ov = resolve("link.sequence", {"book": book_id, "page": page}, store, base=None)
        if ov and ov.get("assign"):
            out = []
            for a in ov["assign"]:
                ci = a.get("caption_index", 0)
                if ci >= len(caps):
                    continue
                order = a.get("step_order") or a.get("regions", [])
                boxes = [regions[i] for i in order if i < len(regions)]
                out.append((caps[ci][0], boxes))
            return out
    return link_page(caps, regions)


def parse_page(pdf: Path, page: int, book: dict, *, store=None, img: np.ndarray | None = None,
               write_keyframes: bool = False, processed_root: Path | None = None,
               repo_root: Path | None = None, retrieved: str = "", dpi: int = 300,
               lang: str = "jpn+eng") -> PageParse:
    """Parse one page into (technique, keyframe) records. write_keyframes=False is the
    non-destructive preview (no PNGs; in-memory crops returned); True writes crops to disk."""
    section = section_for(book["id"], page, store)
    if section.kind == "skip":
        return PageParse(section=section, crops=[] if not write_keyframes else None)
    if img is None:
        img = render_page(pdf, page, dpi)
    h, w = img.shape[:2]

    words = _ocr.words_with_boxes(img, lang=lang, psm=11)
    lines = _group_lines(words)
    if section.is_weapon:
        caps = _weapon_caps(lines, section)
    else:
        caps = []
        for idx, ln in enumerate(lines):
            if is_caption(ln["text"]):
                caps.append((parse_caption(ln["text"], native=_native_for(lines, idx)), ln["top"]))
        caps = merge_bilingual(caps)
    caps = _apply_caption_override(caps, book["id"], page, store)

    regions = _apply_region_ops(_photos.detect_photo_regions(img), book["id"], page, store)
    linked = _apply_link(caps, regions, book["id"], page, store)

    pp = PageParse(section=section, regions=regions, page_size=(w, h),
                   captions=[{"name_romaji": c.name_romaji, "name_native": c.name_native,
                              "slots": c.slots, "raw": c.raw} for c, _ in caps],
                   crops=[] if not write_keyframes else None)
    for seq, (caption, cap_boxes) in enumerate(linked, start=1):
        if not cap_boxes:
            continue
        tech, kfs = _kf.build_records(book, caption, cap_boxes, img, page,
                                      processed_root or Path("."), retrieved, repo_root=repo_root,
                                      section=section, seq=seq, write_images=write_keyframes)
        pp.techniques.append(tech)
        pp.keyframes.extend(kfs)
        if not write_keyframes:
            pp.crops.extend(_kf.crop_regions(img, cap_boxes))
    return pp


def ingest_book(pdf: Path, book: dict, taxonomy_dir: Path, processed_root: Path,
                repo_root: Path, retrieved: str, pages: list[int] | None = None,
                dpi: int = 300, lang: str = "jpn+eng") -> dict:
    store = Store(taxonomy_dir).load()
    total = page_count(pdf)
    pages = pages or list(range(1, total + 1))
    stats = {"pages_scanned": 0, "pages_with_caption": 0, "techniques": 0, "keyframes": 0}

    # The same Refinements the review tool authors are honored on a full re-ingest.
    refstore = _load_refinements(repo_root)
    _captions.apply_lexicon(refstore)

    for page in pages:
        if page < 1 or page > total:
            continue
        if section_for(book["id"], page, refstore).kind == "skip":
            continue
        stats["pages_scanned"] += 1
        pp = parse_page(pdf, page, book, store=refstore, write_keyframes=True,
                        processed_root=processed_root, repo_root=repo_root,
                        retrieved=retrieved, dpi=dpi, lang=lang)
        if not pp.techniques:
            continue
        stats["pages_with_caption"] += 1
        for t in pp.techniques:
            store.upsert("techniques", t)
        store.upsert_many("keyframes", pp.keyframes)
        stats["techniques"] += len(pp.techniques)
        stats["keyframes"] += len(pp.keyframes)

    store.save()
    _captions.reset_lexicon()

    techs = [t for t in store.all("techniques") if t["source"].get("book") == book["id"]]
    kfs = [k for k in store.all("keyframes") if k["source"].get("book") == book["id"]]
    pages_done = sorted({t["source"]["pdf_page"] for t in techs})
    ingested = {"techniques": len(techs), "keyframes": len(kfs),
                "pages_with_content": len(pages_done),
                "page_span": [pages_done[0], pages_done[-1]] if pages_done else None}
    _bookmeta.write_description(book, processed_root, retrieved, ingested=ingested, last_run=stats)
    return stats


def _load_refinements(repo_root: Path):
    """Best-effort load of data/refinements.json; returns None if the primitive/file is absent
    so ingestion still runs seed-only."""
    try:
        from schema.refinement import RefinementStore
    except ImportError:
        return None
    path = Path(repo_root) / "data" / "refinements.json"
    return RefinementStore(path=path) if path.exists() else None
