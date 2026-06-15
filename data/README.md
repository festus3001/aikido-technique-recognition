# data/

Project datasets, DVC-tracked and gitignored (nothing sensitive in git). These are outputs,
derived from the inputs in resources/ and from the crawler.

- `map/`      -- the lineage and federation data map: normalized JSON for persons,
                 organizations, dojos, rank_events, and lineage edges, plus review.json and
                 coverage_report.md. Produced by tools/crawler (spec: docs/atr_13_datamap_crawl).
- `taxonomy/` -- the technique taxonomy artifact: slot vocabulary (attack / technique /
                 direction / form) and technique reference, extracted from books in
                 resources/books and ratified by teachers (Roadmap Phases 1-2).
- `models/`   -- trained model artifacts and evaluation outputs from the builder pipeline
                 (docs/atr_06_toolchain_stack). Versioned; weights are not the sensitive asset.
