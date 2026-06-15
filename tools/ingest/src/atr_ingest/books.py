"""Book registry: canonical metadata for each ingested source.

Each book gets a canonical slug for the processed path and a description file.
Bibliographic data is grounded in the primary source -- each book's colophon
(奥付) and the series advertisement page -- supplemented by OpenLibrary/NDL:

  - per-volume year and printed page count: from the colophons + the Vol.5
    series ad (high confidence, printed in the books)
  - Japanese title, translator, publisher: from the colophons
  - ISBN: NOT printed in the 1973-74 originals; the 0-87040 numbers are the
    Japan Publications Trading distributor's (work-level). Vol.2/Vol.3 are mapped
    by page count (180pp / ~140pp) and flagged inferred; V1/V4/V5 unresolved.
"""

from __future__ import annotations

from pathlib import Path

from .render import page_count
from .util import slugify

SERIES = {
    "author": "Morihiro Saito",
    "author_native": "斉藤 守弘",
    "series": "Traditional Aikido",
    "original_title_native": "合気道 : 剣・杖・体術の理合",
    "translator": "William F. Witt",
    "publisher": "Minato Research & Publishing",
    "publisher_native": "港リサーチ株式会社",
    "publisher_person": "菅原秋孝 (Akitaka Sugawara)",
    "publish_place": "Tokyo, Japan",
    "distributor": "Japan Publications Trading Co. (ISBN prefix 0-87040)",
    "lineage": "iwama",
    "language": ["ja", "en"],
}

PERFORMER = "person:" + slugify(SERIES["author"])  # person:morihiro-saito

# Discovered series ISBNs (Japan Publications Trading), not all volume-mapped.
SERIES_ISBN_CANDIDATES = ["0-87040-266-8", "0-87040-267-6", "0-87040-287-0", "0-87040-372-9 (1989 reprint)"]

# Per-volume facts from the colophons (©year) and the Vol.5 series ad (page counts).
VOLUMES = {
    "Vol.1": {"volume": 1, "subtitle": "Basic Techniques", "year": "1973", "year_conf": "stated",
              "printed_pages": 136, "isbn_10": None, "isbn_conf": None},
    "Vol.2": {"volume": 2, "subtitle": "Advanced Techniques", "year": "1974", "year_conf": "stated",
              "printed_pages": 180, "isbn_10": "0-87040-267-6", "isbn_conf": "inferred (page-count match, 180pp)"},
    "Vol.3": {"volume": 3, "subtitle": "Applied Techniques", "year": "1974", "year_conf": "stated",
              "printed_pages": 140, "isbn_10": "0-87040-287-0", "isbn_conf": "inferred (page-count match, ~140pp)"},
    "Vol.4": {"volume": 4, "subtitle": "Vital Techniques", "year": "1974", "year_conf": "stated",
              "printed_pages": 166, "isbn_10": None, "isbn_conf": None},
    "Vol.5": {"volume": 5, "subtitle": "Training Works Wonders", "year": "1974", "year_conf": "inferred",
              "printed_pages": 148, "isbn_10": None, "isbn_conf": None},
}

_ISBN_NOTE = ("Year/page-count/translator/Japanese-title from each book's colophon (奥付) and the "
              "Vol.5 series ad. No ISBN is printed in the 1973-74 originals; 0-87040 numbers are the "
              "Japan Publications Trading distributor's, mapped to Vol.2 (180pp) and Vol.3 (~140pp) by "
              "page count. V1/V4/V5 ISBN unresolved -- confirm via WorldCat / NDL.")


def _record(v: dict, pdf: Path, pdf_pages: int) -> dict:
    slug = f"saito-traditional-aikido-vol{v['volume']}"
    return {
        "id": slug,
        "author": SERIES["author"],
        "author_native": SERIES["author_native"],
        "series": SERIES["series"],
        "volume": v["volume"],
        "subtitle": v["subtitle"],
        "full_title": f"{SERIES['series']}, Volume {v['volume']}: {v['subtitle']}",
        "publisher": SERIES["publisher"],
        "published": v["year"],
        "language": SERIES["language"],
        "lineage": SERIES["lineage"],
        "performer": PERFORMER,
        "performer_name": SERIES["author"],
        "era": {"start": v["year"], "end": v["year"], "confidence": v["year_conf"],
                "note": "publication year from book colophon (©)"},
        "bibliography": {
            "isbn_10": v["isbn_10"],
            "isbn_13": None,
            "isbn_confidence": v["isbn_conf"],
            "oclc": None, "lccn": None,
            "edition": "1st (Minato Research)",
            "publish_place": SERIES["publish_place"],
            "publisher_native": SERIES["publisher_native"],
            "publisher_person": SERIES["publisher_person"],
            "distributor": SERIES["distributor"],
            "translator": SERIES["translator"],
            "original_title_native": SERIES["original_title_native"],
            "printed_pages": v["printed_pages"],
            "series_isbn_candidates": SERIES_ISBN_CANDIDATES,
            "source": "book colophon (primary) + OpenLibrary/NDL, 2026-06-15",
            "confidence": "mixed (year stated; isbn inferred/unresolved)",
            "note": _ISBN_NOTE,
        },
        "source_pdf": pdf.name,
        "pages": pdf_pages,
        "status": "provisional",
    }


def discover_books(books_dir: Path) -> list[tuple[dict, Path]]:
    """Return [(book_record, pdf_path)] for every Saito PDF on disk."""
    out: list[tuple[dict, Path]] = []
    for pdf in sorted(books_dir.glob("*.pdf")):
        for token, v in VOLUMES.items():
            if token in pdf.name:
                out.append((_record(v, pdf, page_count(pdf)), pdf))
                break
    return out
