"""Backfill observation provenance onto existing taxonomy records (no re-OCR).

Adds the `provenance` object (performer person:slug, era, medium, recording,
lineage) to every technique and keyframe by looking up its source book in the
registry, rewrites each book.json, and reconciles the performer against the
lineage data map (data/map/persons.json)."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from . import bookmeta as _bookmeta
from .books import discover_books
from .store import Store

REPO_ROOT = Path(__file__).resolve().parents[4]
BOOKS_DIR = REPO_ROOT / "resources" / "books" / "raw" / "M.Saito-Traditional Aikido Vol.1-5"
DEFAULT_TAXONOMY = REPO_ROOT / "data" / "taxonomy"
DEFAULT_PROCESSED = REPO_ROOT / "resources" / "books" / "processed"
DATAMAP_PERSONS = REPO_ROOT / "data" / "map" / "persons.json"


def _provenance(book: dict) -> dict:
    return {"performer": book.get("performer"), "performer_name": book.get("performer_name"),
            "era": book.get("era"), "medium": "book", "recording": book["id"],
            "lineage": book.get("lineage")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="atr-ingest-backfill",
                                 description="Backfill observation provenance onto taxonomy records")
    ap.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    ap.add_argument("--processed", type=Path, default=DEFAULT_PROCESSED)
    ap.add_argument("--retrieved", default=date.today().isoformat())
    args = ap.parse_args(argv)

    books = {b["id"]: b for b, _ in discover_books(BOOKS_DIR)}
    store = Store(args.taxonomy).load()

    n = {"techniques": 0, "keyframes": 0, "unmatched": 0}
    for coll in ("techniques", "keyframes"):
        for rec in list(store.data[coll].values()):
            book = books.get(rec.get("source", {}).get("book"))
            if not book:
                n["unmatched"] += 1
                continue
            rec["provenance"] = _provenance(book)
            n[coll] += 1
    store.save()

    # rewrite each book.json with performer/era + recomputed cumulative stats
    for bid, book in books.items():
        techs = [t for t in store.all("techniques") if t["source"].get("book") == bid]
        if not techs:
            continue
        kfs = [k for k in store.all("keyframes") if k["source"].get("book") == bid]
        pages = sorted({t["source"]["pdf_page"] for t in techs})
        ingested = {"techniques": len(techs), "keyframes": len(kfs),
                    "pages_with_content": len(pages),
                    "page_span": [pages[0], pages[-1]] if pages else None}
        _bookmeta.write_description(book, args.processed, args.retrieved, ingested=ingested)

    # reconcile performer against the lineage data map
    resolved = "?"
    if DATAMAP_PERSONS.exists():
        ids = {p["id"] for p in json.loads(DATAMAP_PERSONS.read_text(encoding="utf-8"))}
        performers = {b["performer"] for b in books.values()}
        present = sorted(p for p in performers if p in ids)
        missing = sorted(p for p in performers if p not in ids)
        resolved = f"{len(present)}/{len(performers)} performer(s) resolve into data/map"
        if missing:
            resolved += f"; unresolved: {', '.join(missing)}"

    print(f"Backfilled provenance: {n['techniques']} techniques, {n['keyframes']} keyframes"
          + (f", {n['unmatched']} unmatched" if n["unmatched"] else ""))
    print(f"Performer reconcile: {resolved}")
    problems = store.validate()
    print(f"Validation: {'OK' if not problems else f'{len(problems)} invalid'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
