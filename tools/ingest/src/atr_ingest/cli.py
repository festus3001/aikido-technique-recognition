"""Command line: ingest scanned aikido PDFs into taxonomy + keyframes.

  atr-ingest --vol vol1 --pages 50-90       # a slice of one volume
  atr-ingest --all                          # every volume, every page (long)
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from .books import discover_books
from .pipeline import ingest_book

REPO_ROOT = Path(__file__).resolve().parents[4]
BOOKS_DIR = REPO_ROOT / "resources" / "books" / "raw" / "M.Saito-Traditional Aikido Vol.1-5"
DEFAULT_TAXONOMY = REPO_ROOT / "data" / "taxonomy"
DEFAULT_PROCESSED = REPO_ROOT / "resources" / "books" / "processed"


def parse_pages(spec: str | None) -> list[int] | None:
    if not spec:
        return None
    pages: list[int] = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            pages.extend(range(int(a), int(b) + 1))
        else:
            pages.append(int(part))
    return pages


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="atr-ingest", description="ATR book-ingestion pipeline")
    p.add_argument("--book", help="book by volume number (1-5) or canonical slug (default: all)")
    p.add_argument("--all", action="store_true", help="ingest every book")
    p.add_argument("--pages", help="page range, e.g. 50-90 or 60 or 12,40,55")
    p.add_argument("--dpi", type=int, default=300)
    p.add_argument("--lang", default="jpn+eng", help="tesseract languages")
    p.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    p.add_argument("--processed", type=Path, default=DEFAULT_PROCESSED)
    p.add_argument("--retrieved", default=date.today().isoformat())
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    books = discover_books(BOOKS_DIR)
    if not books:
        print(f"No books found under {BOOKS_DIR}")
        return 1

    if args.book:
        sel = args.book.lower()
        chosen = [(b, p) for b, p in books
                  if b["id"] == sel or str(b["volume"]) == sel or f"vol{b['volume']}" == sel]
        if not chosen:
            have = ", ".join(b["id"] for b, _ in books)
            print(f"Unknown book {args.book}; have: {have}")
            return 1
    elif args.all:
        chosen = books
    else:
        have = ", ".join(b["id"] for b, _ in books)
        print(f"Specify --book <1-5 | slug> or --all. Books: {have}")
        return 1

    pages = parse_pages(args.pages)
    grand = {"pages_scanned": 0, "pages_with_caption": 0, "techniques": 0, "keyframes": 0}
    for book, pdf in chosen:
        print(f"== {book['id']}: {book['full_title']} ==")
        stats = ingest_book(pdf, book, args.taxonomy, args.processed, REPO_ROOT,
                            args.retrieved, pages=pages, dpi=args.dpi, lang=args.lang)
        print(f"   pages {stats['pages_scanned']} | with caption {stats['pages_with_caption']} | "
              f"techniques {stats['techniques']} | keyframes {stats['keyframes']}")
        for k in grand:
            grand[k] += stats[k]

    from .store import Store
    problems = Store(args.taxonomy).load().validate()
    print(f"\nValidation: {'OK' if not problems else f'{len(problems)} invalid record(s)'}")
    for rid, errs in list(problems.items())[:5]:
        print(f"  {rid}: {errs[0]}")

    print(f"\nTotal: {grand['techniques']} techniques, {grand['keyframes']} keyframes from "
          f"{grand['pages_with_caption']}/{grand['pages_scanned']} caption pages")
    print(f"Taxonomy -> {args.taxonomy}/(techniques,keyframes).json")
    print(f"Keyframe images -> {args.processed}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
