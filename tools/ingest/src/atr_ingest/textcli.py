"""Capture text blocks from a book's pages into data/taxonomy/textblocks.json.

  atr-textblocks --book vol1 --pages 26-28 --translate
  atr-textblocks --book vol1                      # all pages, no translation (fast)

Each text block (Japanese prose, the author's English, captions) is OCR'd, language-tagged,
and stored. With --translate, Japanese blocks get a local glossary-tuned translation (Ollama).
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import date
from pathlib import Path

from .books import discover_books
from .cli import BOOKS_DIR, REPO_ROOT
from .render import page_count, render_page
from .textblocks import extract_text_blocks

TEXTBLOCKS = REPO_ROOT / "data" / "taxonomy" / "textblocks.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def _save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def _pages(spec, total):
    if not spec:
        return list(range(1, total + 1))
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def main(argv=None):
    p = argparse.ArgumentParser(prog="atr-textblocks", description="Capture page text blocks")
    p.add_argument("--book", required=True, help="volume number (1-5) or slug")
    p.add_argument("--pages", help="e.g. 26-28 or 40")
    p.add_argument("--translate", action="store_true", help="translate Japanese blocks (Ollama)")
    p.add_argument("--model", default="gemma3:12b")
    p.add_argument("--dpi", type=int, default=300)
    p.add_argument("--min-conf", type=float, default=30.0)
    args = p.parse_args(argv)

    books = {b["id"]: (b, pdf) for b, pdf in discover_books(BOOKS_DIR)}
    sel = args.book.lower()
    match = next(((b, pdf) for bid, (b, pdf) in books.items()
                  if bid == sel or str(b["volume"]) == sel or f"vol{b['volume']}" == sel), None)
    if not match:
        print("unknown book; have:", ", ".join(books)); return 1
    book, pdf = match
    total = page_count(pdf)
    pages = [p for p in _pages(args.pages, total) if 1 <= p <= total]

    glossary = None
    if args.translate:
        from .translate import load_glossary
        glossary = load_glossary()

    provenance = {"performer": book.get("performer"), "performer_name": book.get("performer_name"),
                  "era": book.get("era"), "medium": "book", "recording": book["id"],
                  "lineage": book.get("lineage")}
    retrieved = date.today().isoformat()

    store = [r for r in _load(TEXTBLOCKS)
             if not (r["book"] == book["id"] and r["page"] in pages)]   # purge pages we re-do
    n_blocks = n_ja = n_tr = 0
    for page in pages:
        img = render_page(pdf, page, args.dpi)
        for i, blk in enumerate(extract_text_blocks(img, min_conf=args.min_conf), start=1):
            rec = {"id": f"text:{book['id']}-p{page}-b{i}", "book": book["id"], "page": page,
                   "block": i, "bbox": blk["bbox"], "text": blk["text"], "lang": blk["lang"],
                   "conf": blk["conf"], "translation": None, "translation_model": None,
                   "terms_used": [], "source": {"book": book["id"], "title": book.get("full_title"),
                                                "pdf_page": page},
                   "provenance": provenance, "status": "provisional", "retrieved": retrieved}
            n_blocks += 1
            if blk["lang"] == "ja":
                n_ja += 1
                if args.translate:
                    from .translate import translate
                    en, used = translate(blk["text"], glossary, model=args.model)
                    rec["translation"], rec["translation_model"], rec["terms_used"] = en, args.model, used
                    n_tr += 1
            store.append(rec)
        print(f"  p{page}: blocks so far {n_blocks}", flush=True)

    store.sort(key=lambda r: (r["book"], r["page"], r["block"]))
    _save(TEXTBLOCKS, store)
    print(f"\n{book['id']}: {n_blocks} blocks ({n_ja} Japanese, {n_tr} translated) -> {TEXTBLOCKS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
