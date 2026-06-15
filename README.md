# Aikido Technique Recognition (ATR)

Local-first system that recovers a structured description of an aikido technique from video --
the attack, the technique, the direction (omote/ura), both partners modeled together -- and,
above that, the qualities the names cannot carry. The project enters the field as a peer:
it works with knowledge and collections that already exist, on their holders' terms, and
contributes structure back.

Start with `docs/atr_01_overview` (the front door; it indexes every document) and read
`CLAUDE.md` / `AGENTS.md` before building.

## Project structure

```
ATR/
├── CLAUDE.md / AGENTS.md     project context, conventions, stance, stack policy (same file, two names)
├── README.md                 this map
├── docs/                     project documents, each as paired .md (source) + .docx (readable)
│                             plus the domain graph .svg. Edit markdown; regenerate docx on build.
├── schema/                   the shared data contract: skeleton, parse, contribution
├── resources/                INPUTS -- ingested source material (local-first, DVC-tracked)
│   ├── books/{raw,processed}     printed sources: TIFF masters -> PDF/A + OCR (docs/atr_09)
│   └── videos/{raw,processed}    motion sources: footage -> pose data (docs/atr_06)
├── data/                     OUTPUTS -- derived datasets (DVC-tracked)
│   ├── map/                      lineage & federation data map (from tools/crawler)
│   ├── taxonomy/                 technique taxonomy artifact (from books, teacher-ratified)
│   └── models/                   trained models and eval outputs
├── tools/
│   └── crawler/                  builds data/map from promotion lists + rosters (docs/atr_13)
├── builder/                  Python/conda model-building surface (docs/atr_06)
├── contributor/              FastAPI backend: serving + contribution records
├── web/                      React contributor UI and demos (lookup, compare, contribute)
└── deploy/                   local-first docker-compose
```

## Inputs and outputs at a glance

- **Inputs** live in `resources/` -- books and videos provided by holders, kept on local
  hardware, never pushed to multi-tenant cloud. Each carries provenance and consent terms.
- **Outputs** live in `data/` -- the taxonomy (from books), the lineage/federation map (from
  the crawler), and trained models. All derived, all versioned.
- **The documents** in `docs/` describe the why and how; the code surfaces build the system;
  `tools/` populates the map.

## Documents (docs/)

- `atr_01_overview` -- overview and document index (the front door)
- `atr_02_roadmap` -- staged plan, phase by phase
- `atr_03_onboarding_teacher` -- Start Here for master teachers
- `atr_04_governance_thread` -- governance and stakeholder stance
- `atr_05_domain_graph.svg` -- where the research sits and what feeds it
- `atr_06_toolchain_stack` -- builder/contributor/deploy technical spec
- `atr_09_book_ingestion` -- book scanning and ingestion pipeline
- `atr_10_source_bibliography` -- candidate printed sources
- `atr_11_lineage_tree` -- provisional aikido lineage tree (data-first)
- `atr_12_federation_map` -- US federation & dojo map
- `atr_13_datamap_crawl` -- data-map schema, crawl plan, and agent prompt

## Principles (non-negotiable)

- Local-first. Holder collections stay on holder/project hardware.
- Parse, don't classify. Recover the parts plus a deep-layer representation.
- The teacher's correction is recognized contribution, recorded with attribution and terms.
- All maps and taxonomies are provisional and subject to teacher correction.
