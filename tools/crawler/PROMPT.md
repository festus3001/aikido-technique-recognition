# Crawler Prompt (Claude Code)

Run from the repo root with network access. Full schema and plan: docs/atr_13_datamap_crawl.

```
You are building a normalized data map of aikido organizations, dojos, people, ranks, and
lineage relationships for the ATR project. Read docs/ for project context and conventions
(no em dashes, provenance on every record, provisional + teacher-correctable data).

GOAL
Populate data/map/ with JSON for five entity types -- person, organization, dojo,
rank_event, teaches_relationship. The authoritative contract is
tools/crawler/schema/entities.schema.json (narrative version: docs/atr_13_datamap_crawl.md
section 1); validate every record against it. Every record carries `source` (URLs) and
`retrieved` (date). Use stable slug ids so re-runs merge, not duplicate.

SOURCES (priority order)
1. Aikikai Hombu Kagamibiraki annual promotion lists (aikikai.or.jp, Japanese; normalize
   romaji/kanji names).
2. USAF annual promotions (usaikifed.com/post/<year>-kagamibiraki-promotions) and USAF
   Shihan/Shidoin/Fukushidoin rosters.
3. Federation dojo locators: USAF, Ki Society (4 US federations), AAA/AAI, Shin Kaze,
   Midwest Aikido Center.
4. Individual dojo sites (chief + assistant instructors).
5. Wikipedia / Aikido Journal for dates and lineage edges only (lower confidence).

PLAN (idempotent phases; write/merge to disk after each)
A. Seed organizations from official sites.
B. Parse every available annual promotion list into rank_event rows; create person/dojo as
   encountered. This is the backbone -- do it first and thoroughly, going back as many years
   as published.
C. Walk each federation dojo locator into dojo records; link to orgs; capture chief instructor.
D. For each dojo with a site, fetch its instructors page; extract instructors.
E. Extract teaches_relationship edges using tools/crawler/lineage_seed_sources.md as the
   source list, plus a bounded crawl of Wikipedia aikidoka infoboxes (Teacher / Notable students
   rows on /wiki/ pages); tag stated where the source states the link explicitly, else inferred.
   Then derive inferred edges from overlapping tenures (co-presence) at anchor dojos.
F. Reconcile duplicates (name variants, kanji/romaji), flag conflicts to data/map/review.json.

RULES
- Never assert a lineage edge without a source; tag confidence stated|inferred|contested.
- Promotion-list dojo affiliations are point-in-time; record the date, do not overwrite
  history.
- Rate-limit and cache fetches; respect robots.txt and any stated terms. If a source says no
  reproduction, record only the citation, not the content.
- Output a coverage report: counts per entity, years of promotion data captured, dojos with
  vs. without instructor data, unresolved duplicates.
- Do not invent. Missing field = null. Flag low-confidence rather than guessing.

DELIVERABLES
data/map/{persons,organizations,dojos,rank_events,tenures,edges}.json, data/map/review.json,
and data/map/coverage_report.md.
```
