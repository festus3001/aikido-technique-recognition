"""Command-line entry point: python -m atr_crawler [options].

Runs the phased, idempotent crawl and writes the data map to data/map/. Default
is an offline run (seeds + lineage file + co-presence); --online enables the live
network phases (promotion lists, locators, dojo sites).
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from .fetch import Fetcher
from .phases import Crawler
from .report import write_report
from .validate import validate_store

REPO_ROOT = Path(__file__).resolve().parents[4]  # src/atr_crawler/cli.py -> repo root
DEFAULT_OUT = REPO_ROOT / "data" / "map"
DEFAULT_CACHE = REPO_ROOT / "tools" / "crawler" / ".cache"
DEFAULT_LINEAGE = REPO_ROOT / "tools" / "crawler" / "lineage_seed_sources.md"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="atr_crawler", description="ATR lineage/federation data-map crawler")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output dir (default: data/map)")
    p.add_argument("--lineage", type=Path, default=DEFAULT_LINEAGE, help="lineage source file for Phase E")
    p.add_argument("--retrieved", default=date.today().isoformat(), help="provenance date stamp (YYYY-MM-DD)")
    p.add_argument("--online", action="store_true", help="enable live network phases (B/C/D)")
    p.add_argument("--cache", type=Path, default=DEFAULT_CACHE, help="fetch cache dir")
    p.add_argument("--min-delay", type=float, default=2.0, help="min seconds between hits to a host")
    p.add_argument("--timeout", type=float, default=45.0, help="per-request timeout seconds (some hosts are slow)")
    p.add_argument("--strict", action="store_true", help="fail if any record is schema-invalid")
    p.add_argument("--apply-merges", action="store_true",
                   help="Phase F: merge high-confidence name-variant duplicates (default: review only)")
    p.add_argument("--phase-d", action="store_true",
                   help="crawl individual dojo websites for instructors (opt-in; many external hosts)")
    p.add_argument("--max-dojo-sites", type=int, default=None,
                   help="cap how many dojo websites Phase D visits")
    p.add_argument("--wiki-max", type=int, default=80,
                   help="Phase E: max Wikipedia articles to crawl for lineage (online)")
    p.add_argument("--no-wiki", action="store_true", help="skip the Phase E Wikipedia crawl")
    p.add_argument("--no-save", action="store_true", help="run without writing output (dry run)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    fetcher = Fetcher(args.cache, min_delay=args.min_delay, timeout=args.timeout) if args.online else None
    crawler = Crawler(args.out, retrieved=args.retrieved, lineage_path=args.lineage, fetcher=fetcher)
    crawler.run(online=args.online, apply_merges=args.apply_merges,
                phase_d=args.phase_d, dojo_site_limit=args.max_dojo_sites,
                wiki=not args.no_wiki, wiki_max=args.wiki_max)

    problems = validate_store(crawler.store, strict=args.strict)

    if args.no_save:
        print("Dry run: nothing written.")
        return 0

    written = crawler.store.save()
    paths = write_report(args.out, crawler.store, crawler.copresence, crawler.lineage_registry,
                         problems, crawler.reconcile)
    print(f"\nWrote {len(written)} collection file(s) to {args.out}")
    print(f"Report: {paths['report']}")
    print(f"Review: {paths['review']}")
    if problems:
        print(f"WARNING: {len(problems)} record(s) failed validation (see report).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
