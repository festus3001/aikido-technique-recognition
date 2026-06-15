# Lineage / federation data map

Output of `tools/crawler` (see docs/atr_13_datamap_crawl.md). Every record is provisional and
subject to teacher correction; each carries `source` + `retrieved` provenance. Regenerate with
`conda run -n atr-tools atr-crawler --online --strict`; runs are idempotent (merge by stable id).

## Files
- `persons.json`, `organizations.json`, `dojos.json` -- entities
- `rank_events.json` -- promotion backbone (USAF Kagamibiraki, currently 2022-2026)
- `tenures.json` -- person-at-dojo over time; overlaps drive co-presence
- `edges.json` -- lineage (teaches_relationship): `stated` from the lineage file + Wikipedia
  infoboxes, `inferred` from co-presence; an edge attested by several merges by id keeps all sources
- `atr_map.sqlite` -- relational projection of the JSON, rebuilt with `atr-crawler-db`. Scalars
  become columns, nested fields flatten, list fields (sources/aliases/dojo orgs/instructors)
  become child tables. Readable views join ids to names: `v_lineage` (student/teacher),
  `v_promotions` (person/dan/year/dojo), `v_dojo`, `v_tenure`. Query with `sqlite3`.
- `coverage_report.md` -- counts, promotion-year span, co-presence overlaps, pending sources
- `review.json` -- validation failures, contested records, and Phase F `merge_candidates`
  (name-variant duplicate persons): `high` are auto-mergeable, `medium` need human confirmation

## Provenance notes
- Promotion data is fetched and parsed from usaikifed.com; source text is recorded verbatim,
  including its own typos. Lower grades (1st-4th dan) are dojo-level and not published here. The
  Aikikai Hombu official Kagamibiraki name list is not published on the web (verified 2026-06),
  so each national body's republication is the practical source.
- Lineage edges come from `lineage_seed_sources.md` and a bounded Wikipedia infobox crawl
  (Phase E). Wikipedia uses article titles as person ids, so a few Japanese names are surname-
  first and may need Phase F reconcile to align with given-first names from other sources.
- Dojo instructors and locations come from federation locators (Phase C): USAF, Ki Society,
  AAA/AAI, and Shin Kaze. `chief_instructor` is the locator's current chief; historical roles
  live in `tenures.json`. Ki Society detail pages also yield its sub-federations as
  `organization` records; AAA international dojos are routed to org:aai. Phase D (individual dojo
  sites) and the Aikikai Hombu official promotion list are not yet run.
- Seed tenure years are `inferred`/`provisional` reconstructions pending primary-source
  confirmation.
- Phase F reconcile finds name-variant duplicate persons (e.g. "William Ross" / "William R.
  Ross") across sources. By default it only writes a review queue; `atr-crawler --apply-merges`
  merges the high-confidence tier (combining aliases/sources, re-pointing every reference).
  Clusters with conflicting variants (e.g. different middle initials) are never auto-merged.
- Phase D (individual dojo websites) is opt-in and not in the committed data: `atr-crawler
  --online --phase-d [--max-dojo-sites N]`. It is high-precision and low-yield -- it follows a
  site's own instructor/about links and takes a name only when it sits next to an explicit
  signal (Chief Instructor label, "Sensei", or a dan rank), tagging each
  `instructor extracted from dojo website (unverified)`. It touches many external hosts, so run
  it deliberately; the agent route (PROMPT.md) is better for high-quality per-site extraction.
