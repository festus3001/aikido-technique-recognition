# crawler

Builds the aikido lineage and federation data map. See docs/atr_13_datamap_crawl for the
full specification (schema, sources, phased plan). This directory holds the implementation
and the ready-to-run agent prompt.

## Layout
- `schema/`     -- `entities.schema.json`: JSON Schema (draft 2020-12) for the six entity types.
- `src/atr_crawler/` -- crawler implementation (package). Phases A-F: store, validation, fetch,
                   usaf (B), locators (C), dojo_sites (D), lineage + wikipedia (E), copresence,
                   reconcile (F), reporting, CLI; `seeds/` holds Phase A seed data.
- `lineage_seed_sources.md` -- Phase E input: curated source registry for lineage edges.
- `environment.yml` -- conda env (`atr-tools`) for the crawler.
- `PROMPT.md`   -- the agent-driven alternative for live extraction (network required).
- output -> ../../data/map/{persons,organizations,dojos,rank_events,tenures,edges}.json
            plus review.json and coverage_report.md

## Run
One-time setup:
```
conda env create -f tools/crawler/environment.yml
conda run -n atr-tools pip install -e tools/crawler
```
Offline run (seeds + lineage file + co-presence), with schema validation:
```
conda run -n atr-tools atr-crawler --strict
```
Full live run (USAF promotions, four federation locators, Wikipedia lineage), validated:
```
conda run -n atr-tools atr-crawler --online --strict
```
Flags:
- `--online` -- enable network phases (B promotions, C locators, E Wikipedia lineage).
- `--apply-merges` -- Phase F: merge high-confidence name-variant duplicates (default: review only).
- `--phase-d [--max-dojo-sites N]` -- crawl individual dojo websites for instructors (opt-in;
  many external hosts, high-precision/low-yield).
- `--wiki-max N` / `--no-wiki` -- bound or skip the Phase E Wikipedia crawl.
- `--timeout S` -- per-request timeout (some hosts are slow).

Idempotent: re-runs merge by stable id. Respects robots.txt (fetched with the crawler's own UA)
and stated terms; records citations only for no-reproduction sources. The Aikikai Hombu official
promotion list is not web-published, so Phase B uses national-body republications (USAF).

## SQLite
The JSON collections are the canonical output; project them into a queryable database with:
```
conda run -n atr-tools atr-crawler-db        # writes data/map/atr_map.sqlite
conda run -n atr-tools sqlite3 -box data/map/atr_map.sqlite "SELECT * FROM v_lineage LIMIT 10;"
```
Views: `v_lineage` (student/teacher/confidence), `v_promotions` (person/dan/year/dojo),
`v_dojo` (dojo/location/chief), `v_tenure`. Rebuild any time -- it is a pure projection of JSON.

## Refresh cadence
- Promotion lists (the backbone): re-run every January after Kagamibiraki.
- Federation rosters and dojo sites: quarterly.
