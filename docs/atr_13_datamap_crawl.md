# ATR -- Lineage & Federation Data Map: Schema and Crawl Plan

The hand-compiled federation map (the federation map document) and the lineage tree are
sketches. This document specifies the actual data map -- a normalized schema for people,
organizations, dojos, ranks, and the relationships among them -- and a repeatable crawl that
populates it from authoritative sources, including annual promotion lists. It also contains a
ready-to-run Claude Code prompt.

Principle: the map is built from primary, structured, dated sources (federation rosters and
promotion lists) rather than prose, so it can be refreshed on a schedule and every fact
carries provenance. As with all project data, it is provisional and subject to teacher
correction; it records what sources say, not a ruling on contested lineage.

---

## 1. Data model

Six entity types. Stored as JSON (one file per type); each record carries `source` and
`retrieved` provenance. The machine-readable contract is
`tools/crawler/schema/entities.schema.json`; the records below are illustrative.

### person
```
{
  "id": "person:slug",            // stable slug, e.g. "person:akira-tohei"
  "name_romaji": "Akira Tohei",
  "name_native": "藤平 明",         // where known; null otherwise
  "aliases": ["A. Tohei"],
  "born": "1929", "died": "1999", // year strings or null
  "current_rank": {"dan": 8, "title": "shihan"},  // highest known
  "deceased": true,
  "notes": "Not to be confused with Koichi Tohei (Ki Society).",
  "source": ["url", ...],
  "retrieved": "2026-06-08",
  "status": "provisional"
}
```

### organization  (federation / association / alliance)
```
{
  "id": "org:slug",               // "org:usaf"
  "name": "United States Aikido Federation",
  "abbrev": "USAF",
  "type": "federation",           // federation | association | alliance | hombu
  "lineage": "aikikai",           // aikikai | ki-society | toyoda | yoshinkan | other
  "parent_org": "org:aikikai-hombu", // recognizing body, or null
  "hq": "New York, USA",
  "founded": "1976",
  "governance": "Technical Committee + Board",
  "website": "usaikifed.com",
  "source": ["url"], "retrieved": "2026-06-08", "status": "provisional"
}
```

### dojo
```
{
  "id": "dojo:slug",              // "dojo:new-york-aikikai"
  "name": "New York Aikikai",
  "org": ["org:usaf"],            // affiliations (can be >1 over time)
  "location": {"city": "New York", "region": "NY", "country": "USA"},
  "chief_instructor": "person:slug",
  "instructors": ["person:slug", ...],  // shidoin / fukushidoin where listed
  "website": "nyaikikai.com",
  "source": ["url"], "retrieved": "2026-06-08", "status": "provisional"
}
```

### rank_event   (the spine -- one row per promotion, from promotion lists)
```
{
  "id": "rank:person+date+dan",
  "person": "person:slug",        // create person if new
  "dan": 5,
  "title": null,                  // "shihan" when conferred
  "date": "2026-01-11",           // Kagamibiraki date or list year
  "conferred_by": "org:aikikai-hombu",
  "via_org": "org:usaf",          // the body that submitted/recognized
  "dojo": "dojo:slug",            // affiliation at time of promotion
  "source": ["url"], "retrieved": "2026-06-08"
}
```

### tenure   (a person at a dojo over time -- the co-presence signal)
```
{
  "id": "tenure:person+dojo+start",
  "person": "person:slug",
  "dojo": "dojo:slug",
  "role": "uchi-deshi",           // founder | chief-instructor | instructor |
                                  // uchi-deshi | deshi | student | visiting | unspecified
  "start": "1955", "end": "1964", // year strings or null
  "confidence": "inferred",       // stated | inferred | contested
  "notes": "approximate; pending primary-source confirmation",
  "source": ["url"], "retrieved": "2026-06-11", "status": "provisional"
}
```

### teaches_relationship  (student <- teacher; the lineage edges)
```
{
  "id": "edge:student+teacher",
  "student": "person:slug",
  "teacher": "person:slug",
  "kind": "uchi-deshi",           // uchi-deshi | direct-student | seminar | unspecified
  "period": "1958-1969",          // where known
  "confidence": "stated",         // stated | inferred | contested
  "source": ["url"], "retrieved": "2026-06-08", "status": "provisional"
}
```

Notes:
- `rank_event` is the backbone. Promotion lists give (name, dan, dojo, year) every January;
  accumulating them across years yields people, their dojo affiliations, and rank histories
  with dates -- the most reliable structured signal available.
- Lineage edges (`teaches_relationship`) are the contested part. They come from prose bios and
  must carry `confidence` and `source`; never assert an edge without one.
- `tenure` reconstructs the decades before promotion lists are available. The richest structured
  signal those decades leave is who trained where, and when. Overlapping tenures at the same
  anchor dojo -- the major places where founders and senior shihan taught -- are co-presence:
  where one held a teaching role and the other a student role during the overlap, an `inferred`
  edge is emitted; peer overlaps are recorded for the report but not asserted. The postwar
  uchi-deshi cohort overlapping at Aikikai Hombu, then dispersing to found the US anchor dojos,
  is the worked example. `dojo` carries `anchor` and `founded` to support this.
- All ids are stable slugs so re-crawls merge rather than duplicate.

---

## 2. Authoritative sources (priority order)

1. **Aikikai Hombu Kagamibiraki promotion list (annual, January).** The official Aikikai
   Foundation list; in principle the single richest source, ~1,000+ promotions per year.
   NOTE (verified 2026-06): aikikai.or.jp does NOT publish the list of promoted names on the
   web -- its grading page (/hombudojo/grading/) carries examination requirements, not a roster.
   The list is announced at the ceremony and in print. The practical web-accessible substitute
   is each national body's republication of its own members' entries (item 2), which is what the
   implemented Phase B uses.
2. **USAF promotions (annual).** USAF republishes its members' Kagamibiraki promotions as
   (name, dan, dojo) -- e.g. usaikifed.com/post/<year>-kagamibiraki-promotions -- plus its
   Shihan / Shidoin / Fukushidoin rosters.
3. **Federation rosters and dojo locators.** USAF (services.usaikifed.com/dojos), Ki Society
   (ki-society.com/nation/usa and the four US federations), AAA/AAI (aaa-aikido.com locator),
   Shin Kaze (shinkazeaikidoalliance.com), Midwest Aikido Center (midwestaikidocenter.org).
4. **Individual dojo sites.** For chief instructor and assistant-instructor names; the long
   tail, crawled from each federation's locator.
5. **Reference cross-checks.** Wikipedia / Aikido Journal for dates and lineage edges only,
   flagged lower-confidence than primary rosters.

Cautions: the Hombu list is large and Japanese-language (needs name normalization
romaji<->kanji); promotion lists rarely include teacher links (those come from bios); dojo
affiliations on promotion lists are point-in-time and change.

---

## 3. Crawl plan

Phased, idempotent, provenance-stamped. Each phase writes/merges into the JSON store by stable
id; re-runs update rather than duplicate.

- **Phase A -- organizations and anchors.** Seed the orgs from their official sites, plus the
  anchor dojos, the founder/uchi-deshi cohort (`person`), and their `tenure` records.
  Hand-confirmable, small, stable. Tenure years are `inferred`/`provisional` pending
  primary-source confirmation.
- **Phase B -- promotion lists (the spine).** Pull every available annual list (Hombu official
  + USAF republications + other national bodies). Parse to `rank_event` rows; create `person`
  and `dojo` records as encountered. Go back as many years as are published. This alone builds
  most of the people-and-dojo graph with dates.
- **Phase C -- federation rosters / locators.** Walk each federation's dojo locator to a
  `dojo` list; capture chief instructor where shown. Link dojos to orgs.
- **Phase D -- dojo sites (long tail).** For each dojo with a website, fetch the
  instructors/about page; extract chief and assistant instructors into `person` + update
  `dojo.instructors`. Rate-limit and cache.
- **Phase E -- lineage edges.** Two sources, both tagged `stated` and merged by edge id:
  (a) the hand-curated `tools/crawler/lineage_seed_sources.md` registry (inline infobox edges +
  prose sources), and (b) a bounded breadth-first crawl of Wikipedia aikidoka article infoboxes
  (`Teacher` / `Notable students` rows, robots-allowed /wiki/ pages), starting from seed teachers
  and following the links, also reading dan and the Japanese name. Tag `stated` only where the
  source states the link explicitly, otherwise `inferred`; never overwrite a `stated` edge with
  an `inferred` one. An edge attested by Wikipedia, the registry, and co-presence ends up
  `stated` carrying all three provenances.
- **Co-presence derivation.** After tenures are loaded, derive `inferred` edges from
  overlapping tenures (see the tenure note in section 1). These merge with Phase E edges by id,
  so an edge attested both by an explicit source and by co-presence ends up `stated` with both
  provenances.
- **Phase F -- reconcile.** Merge duplicate persons (romaji variants, kanji), resolve dojo
  renames, flag conflicts for human review. Output a review queue, not silent overwrites.

Refresh cadence: re-run Phase B every January after Kagamibiraki; Phases C-D quarterly.

---

## 4. Claude Code prompt (ready to run)

The runnable prompt lives with the tool, at `tools/crawler/PROMPT.md` -- a single canonical
copy so the two never drift. Open Claude Code at the repo root, with network access, and
follow it. It writes to `data/map/` and validates every record against
`tools/crawler/schema/entities.schema.json`.

---

## 5. Why promotion lists are the right backbone

A roster scraped once is stale immediately and has no dates. The Kagamibiraki lists are
published every January, name each promoted person with their dojo, and span decades. Treating
each promotion as a dated event yields, for free: who exists, what rank they hold and when they
got it, which dojo they belonged to at that time, and -- accumulated -- the growth and movement
of the whole community over time. It is the closest thing to a census the art publishes, and it
is structured. The federation rosters and dojo sites then fill in current chief-instructor
assignments and the lineage bios fill in teacher edges.

---

_ATR · data map schema & crawl plan · rev 1 · 2026-06-08 · draft_