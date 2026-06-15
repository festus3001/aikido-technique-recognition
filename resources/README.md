# resources/

Source material the project ingests. Local-first: holder collections live here on project or
holder hardware, never pushed to multi-tenant cloud. Everything in here is gitignored content
(DVC-tracked); only this README and the structure are committed.

## books/
Printed reference sources for the taxonomy bootstrap (Roadmap Phase 1).
- `raw/`       -- archival masters as captured: lossless TIFF per page, per the book
                  ingestion spec (docs/atr_09_book_ingestion). One subfolder per book.
- `processed/` -- derived artifacts: PDF/A searchable copies, ALTO/hOCR, cropped figures
                  with coordinates, and the per-page layout records.

Capture standard: 400 ppi minimum, 24-bit color masters, lossless TIFF. See
docs/atr_09_book_ingestion for full standards, layout/positional capture, and rights rules.
Candidate sources: docs/atr_10_source_bibliography. Clear rights before ingesting any book.

## videos/
Motion sources for the later video ingestion sub-projects (Roadmap Phase 3+).
- `raw/`       -- original footage as received from a holder, untouched. One subfolder per
                  source/collection, with its provenance and consent terms recorded.
- `processed/` -- pose-extracted and represented data (canonical skeleton schema), per the
                  toolchain spec (docs/atr_06_toolchain_stack).

Holder collections stay on holder/project hardware. Record provenance and machine-readable
consent terms for every source before processing.
