"""Write a description file into each book's processed folder.

Drops `book.json` (canonical metadata + ingestion summary) and a human-readable
`README.md`, so each folder on disk explains the source it came from."""

from __future__ import annotations

import json
from pathlib import Path


def write_description(book: dict, processed_root: Path, retrieved: str,
                      ingested: dict | None = None, last_run: dict | None = None) -> Path:
    folder = processed_root / book["id"]
    folder.mkdir(parents=True, exist_ok=True)

    record = {**book, "retrieved": retrieved}
    if ingested:
        record["ingested"] = ingested          # cumulative, book-scoped (authoritative)
    if last_run:
        record["last_run"] = last_run          # the most recent invocation only
    (folder / "book.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        f"# {book['full_title']}",
        "",
        f"- Author: {book['author']} ({book['author_native']})",
        f"- Series: {book['series']}, volume {book['volume']}",
        f"- Original title: {book['bibliography']['original_title_native']} (translator: {book['bibliography']['translator']})",
        f"- Published: {book['published']} (©, from colophon) -- {book['publisher']} / {book['bibliography']['publisher_native']}, {book['bibliography']['publish_place']}",
        f"- Distributor: {book['bibliography']['distributor']}",
        f"- ISBN: {book['bibliography'].get('isbn_10') or 'unresolved per volume'} ({book['bibliography'].get('isbn_confidence') or 'see series candidates'})",
        f"- Printed pages: {book['bibliography']['printed_pages']}",
        f"- Lineage: {book['lineage']}",
        f"- Language: {', '.join(book['language'])}",
        f"- Source PDF: {book['source_pdf']} ({book['pages']} pages)",
        "",
        "Processed by tools/ingest. Each subfolder is one technique caption found in the book;",
        "`step_NN.png` are the instructional photos in order, tagged in",
        "`data/taxonomy/keyframes.json` as ground-truth keyframes. All provisional, pending",
        "teacher ratification.",
    ]
    if ingested:
        span = ingested.get("page_span")
        span_txt = f" (pages {span[0]}-{span[1]})" if span else ""
        lines += ["", f"Ingested so far: {ingested.get('techniques', 0)} techniques, "
                  f"{ingested.get('keyframes', 0)} keyframes across "
                  f"{ingested.get('pages_with_content', 0)} pages{span_txt}. Last updated {retrieved}."]
    readme = folder / "README.md"
    readme.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return folder
