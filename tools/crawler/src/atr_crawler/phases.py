"""Phase orchestration.

A. organizations         seeded from official sites (offline)
   anchors + cohort      seeded persons, dojos, tenures (offline)
B. promotion lists       rank_events backbone (live network; parser contract below)
C. federation locators   dojos + chief instructors (live network)
D. dojo sites            instructor pages (live network)
E. lineage edges         parsed from lineage_seed_sources.md (offline)
   co-presence           inferred edges from overlapping tenures (offline)
F. reconcile             duplicate-person candidates -> review queue (offline)

The live phases (B, C, D) are source-specific scrapers. They are wired here with
a clear parser contract -- each takes a source URL and returns records matching
the schema -- but the per-source HTML parsers are deliberately left to a live run
rather than guessed offline. Running them without parsers logs the gap; it does
not invent data.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import copresence as _copresence
from . import dojo_sites as _dojo_sites
from . import lineage as _lineage
from . import locators as _locators
from . import reconcile as _reconcile
from . import usaf as _usaf
from . import wikipedia as _wikipedia
from .fetch import Fetcher
from .store import JsonStore

# Years with a published USAF Kagamibiraki post (usaikifed.com blog starts 2022).
USAF_YEARS = list(range(2022, 2027))

SEEDS_DIR = Path(__file__).resolve().parent / "seeds"


class Crawler:
    def __init__(self, out_dir: str | Path, retrieved: str,
                 lineage_path: str | Path | None = None,
                 fetcher: Fetcher | None = None):
        self.store = JsonStore(out_dir).load()
        self.out_dir = Path(out_dir)
        self.retrieved = retrieved
        self.lineage_path = lineage_path
        self.fetcher = fetcher
        self.copresence: dict = {"edges": [], "pairs": []}
        self.lineage_registry: list[str] = []
        self.reconcile: dict = {"high": [], "medium": []}

    # -- seed loading -----------------------------------------------------
    def _load_seed(self, collection: str, filename: str) -> int:
        path = SEEDS_DIR / filename
        if not path.exists():
            return 0
        records = json.loads(path.read_text(encoding="utf-8"))
        for rec in records:
            self.store.upsert(collection, rec)
        return len(records)

    def phase_a_seed(self) -> None:
        n_org = self._load_seed("organizations", "organizations.json")
        n_per = self._load_seed("persons", "persons.json")
        n_dojo = self._load_seed("dojos", "dojos.json")
        n_ten = self._load_seed("tenures", "tenures.json")
        print(f"Phase A (seed): {n_org} orgs, {n_per} persons, {n_dojo} dojos, {n_ten} tenures")

    # -- live phases (parser contract; no-op without a parser) ------------
    def _require_fetcher(self, phase: str) -> bool:
        if self.fetcher is None:
            print(f"{phase}: skipped (no fetcher; pass --online to enable network fetches)")
            return False
        return True

    def phase_b_promotions(self, years: list[int] | None = None) -> None:
        """Parse USAF Kagamibiraki annual promotion lists into rank_event rows.

        Fetches each year's post, parses dan promotions into rank_events (creating
        person/dojo as encountered), and records Shihan-title conferrals as person
        notes. Years without a published post are skipped.
        """
        if not self._require_fetcher("Phase B (promotions)"):
            return
        years = years or USAF_YEARS
        n_events = n_persons = n_dojos = n_shihan = 0
        years_seen: list[int] = []
        for year in years:
            url = _usaf.USAF_URL.format(year=year)
            html = self.fetcher.get(url)
            if not html:
                continue
            parsed = _usaf.parse_kagamibiraki(_usaf.html_to_text(html), year, self.retrieved, url)
            if not parsed["rank_events"] and not parsed["shihan_titles"]:
                continue
            years_seen.append(year)
            for p in parsed["persons"]:
                self.store.upsert("persons", p)
            for d in parsed["dojos"]:
                self.store.upsert("dojos", d)
            for e in parsed["rank_events"]:
                self.store.upsert("rank_events", e)
            n_events += len(parsed["rank_events"])
            n_persons += len(parsed["persons"])
            n_dojos += len(parsed["dojos"])
            n_shihan += len(parsed["shihan_titles"])
        span = f"{min(years_seen)}-{max(years_seen)}" if years_seen else "none"
        print(f"Phase B (USAF promotions): {n_events} rank_events across {len(years_seen)} years "
              f"({span}); {n_persons} persons, {n_dojos} dojos, {n_shihan} shihan titles")

    def phase_c_locators(self) -> None:
        """Walk federation dojo locators into dojo + instructor records.

        Dojo ids derive from the name (same as Phase B), so locator data enriches
        the promotion-list dojos with chief instructor, location, and website.
        Federations without a parser yet are logged as pending.
        """
        if not self._require_fetcher("Phase C (federation locators)"):
            return
        pending: list[str] = []
        for entry in _locators.LOCATORS:
            crawl_key = entry["crawl"]
            if crawl_key is None:
                pending.append(entry["org"])
                continue
            parsed = _locators.CRAWLERS[crawl_key](self.fetcher, entry["org"], entry["url"], self.retrieved)
            for o in parsed.get("orgs", []):
                self.store.upsert("organizations", o)
            for d in parsed["dojos"]:
                self.store.upsert("dojos", d)
            for p in parsed["persons"]:
                self.store.upsert("persons", p)
            print(f"Phase C: {entry['org']} -> {len(parsed['dojos'])} dojos, "
                  f"{len(parsed['persons'])} instructors, {len(parsed.get('orgs', []))} sub-orgs")
        if pending:
            print(f"Phase C: {len(pending)} federation locator(s) pending a parser: {', '.join(pending)}")

    def phase_d_dojo_sites(self, limit: int | None = None) -> None:
        """Crawl individual dojo websites for instructors (opt-in, bounded).

        High-precision and low-yield: only names next to an explicit signal are
        taken. Updates dojo.instructors (union) and fills chief_instructor only
        when a dojo has none; never overwrites a chief from Phase C.
        """
        if not self._require_fetcher("Phase D (dojo sites)"):
            return
        result = _dojo_sites.crawl_dojo_sites(self.fetcher, self.store.all("dojos"),
                                              self.retrieved, limit=limit)
        for p in result["persons"]:
            self.store.upsert("persons", p)
        n_updated = 0
        for dojo_id, upd in result["dojo_updates"].items():
            dojo = self.store.data["dojos"].get(dojo_id)
            if not dojo:
                continue
            patch: dict = {"id": dojo_id, "instructors": upd["instructors"], "source": [upd["source"]]}
            if upd["chief"] and not dojo.get("chief_instructor"):
                patch["chief_instructor"] = upd["chief"]
            self.store.upsert("dojos", patch)
            n_updated += 1
        print(f"Phase D (dojo sites): {len(result['persons'])} instructors extracted, "
              f"{n_updated} dojos updated"
              + (f" (limited to {limit} sites)" if limit else ""))

    # -- offline phases ---------------------------------------------------
    def phase_e_lineage(self, wiki: bool = False, wiki_max: int = 80) -> None:
        parsed = _lineage.parse_lineage_sources(self.lineage_path, self.retrieved)
        for person in parsed["persons"]:
            self.store.upsert("persons", person)
        for edge in parsed["edges"]:
            self.store.upsert("edges", edge)
        self.lineage_registry = parsed["registry"]
        print(f"Phase E (lineage file): {len(parsed['edges'])} stated edges, "
              f"{len(parsed['persons'])} person stubs, "
              f"{len(parsed['registry'])} prose sources registered")

        if wiki and self.fetcher is not None:
            wp = _wikipedia.crawl_wikipedia(self.fetcher, self.retrieved, max_articles=wiki_max)
            for person in wp["persons"]:
                self.store.upsert("persons", person)
            for edge in wp["edges"]:
                self.store.upsert("edges", edge)
            print(f"Phase E (Wikipedia): {wp['articles_visited']} articles, "
                  f"{len(wp['edges'])} stated edges, {len(wp['persons'])} persons")

    def derive_copresence(self) -> None:
        result = _copresence.derive_copresence(self.store.all("tenures"))
        for edge in result["edges"]:
            self.store.upsert("edges", edge)
        self.copresence = result
        directional = sum(1 for p in result["pairs"] if p["directional"])
        print(f"Co-presence: {len(result['pairs'])} overlapping pairs, "
              f"{len(result['edges'])} inferred edges ({directional} directional)")

    def phase_f_reconcile(self, apply_merges: bool = False) -> None:
        """Find name-variant duplicate persons. High-confidence clusters are
        merged when apply_merges is set; otherwise everything goes to review."""
        candidates = _reconcile.find_candidates(self.store.all("persons"))
        n_high = len(candidates["high"])
        n_medium = len(candidates["medium"])

        absorbed = 0
        if apply_merges and candidates["high"]:
            absorbed = _reconcile.apply_merges(self.store, candidates["high"])
            # Recompute after merging so the review queue reflects what remains.
            candidates = _reconcile.find_candidates(self.store.all("persons"))

        self.reconcile = candidates
        action = f"merged {absorbed} duplicate(s); " if apply_merges else ""
        print(f"Phase F (reconcile): {action}{n_high} high-confidence cluster(s), "
              f"{n_medium} medium pair(s) for review"
              + ("" if apply_merges else " (use --apply-merges to merge the high tier)"))

    # -- orchestration ----------------------------------------------------
    def run(self, online: bool = False, apply_merges: bool = False,
            phase_d: bool = False, dojo_site_limit: int | None = None,
            wiki: bool = True, wiki_max: int = 80) -> None:
        self.phase_a_seed()
        if online:
            self.phase_b_promotions()
            self.phase_c_locators()
            if phase_d:
                self.phase_d_dojo_sites(limit=dojo_site_limit)
        self.phase_e_lineage(wiki=online and wiki, wiki_max=wiki_max)
        self.derive_copresence()
        self.phase_f_reconcile(apply_merges=apply_merges)
