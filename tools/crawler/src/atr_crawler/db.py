"""Build a SQLite database from the data/map JSON collections.

The JSON files are the canonical, idempotent crawler output; this projects them
into a queryable relational database. Scalar fields become columns; nested fields
are flattened (current_rank -> dan/title, location -> city/region/country); list
fields (sources, aliases, dojo orgs, dojo instructors) become child tables. A set
of views joins ids to names so the data is directly readable:

    v_lineage     student / teacher / kind / confidence
    v_promotions  person / dan / year / dojo
    v_dojo        dojo / location / chief instructor
    v_tenure      person / dojo / role / years

Rebuild any time: it is a pure projection of the JSON, dropped and recreated.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE persons (
  id TEXT PRIMARY KEY, name_romaji TEXT, name_native TEXT, born TEXT, died TEXT,
  deceased INTEGER, notes TEXT, status TEXT, retrieved TEXT,
  current_rank_dan INTEGER, current_rank_title TEXT
);
CREATE TABLE organizations (
  id TEXT PRIMARY KEY, name TEXT, abbrev TEXT, type TEXT, lineage TEXT,
  parent_org TEXT REFERENCES organizations(id), hq TEXT, founded TEXT,
  governance TEXT, website TEXT, status TEXT, retrieved TEXT
);
CREATE TABLE dojos (
  id TEXT PRIMARY KEY, name TEXT, loc_city TEXT, loc_region TEXT, loc_country TEXT,
  chief_instructor TEXT REFERENCES persons(id), founded TEXT, anchor INTEGER,
  website TEXT, status TEXT, retrieved TEXT
);
CREATE TABLE rank_events (
  id TEXT PRIMARY KEY, person TEXT REFERENCES persons(id), dan INTEGER, title TEXT,
  date TEXT, conferred_by TEXT REFERENCES organizations(id),
  via_org TEXT REFERENCES organizations(id), dojo TEXT REFERENCES dojos(id), retrieved TEXT
);
CREATE TABLE tenures (
  id TEXT PRIMARY KEY, person TEXT REFERENCES persons(id), dojo TEXT REFERENCES dojos(id),
  role TEXT, start TEXT, end TEXT, confidence TEXT, notes TEXT, status TEXT, retrieved TEXT
);
CREATE TABLE edges (
  id TEXT PRIMARY KEY, student TEXT REFERENCES persons(id), teacher TEXT REFERENCES persons(id),
  kind TEXT, period TEXT, confidence TEXT, notes TEXT, status TEXT, retrieved TEXT
);
CREATE TABLE person_aliases (person_id TEXT REFERENCES persons(id), alias TEXT);
CREATE TABLE dojo_orgs (dojo_id TEXT REFERENCES dojos(id), org_id TEXT REFERENCES organizations(id));
CREATE TABLE dojo_instructors (dojo_id TEXT REFERENCES dojos(id), person_id TEXT REFERENCES persons(id));
CREATE TABLE sources (entity_type TEXT, entity_id TEXT, url TEXT);

CREATE INDEX ix_edges_teacher ON edges(teacher);
CREATE INDEX ix_edges_student ON edges(student);
CREATE INDEX ix_rank_person ON rank_events(person);
CREATE INDEX ix_rank_dojo ON rank_events(dojo);
CREATE INDEX ix_tenure_dojo ON tenures(dojo);
CREATE INDEX ix_dojo_instr ON dojo_instructors(person_id);
CREATE INDEX ix_sources_entity ON sources(entity_type, entity_id);

CREATE VIEW v_lineage AS
  SELECT e.id, s.name_romaji AS student, t.name_romaji AS teacher,
         e.kind, e.confidence, e.period, e.notes
  FROM edges e JOIN persons s ON s.id = e.student JOIN persons t ON t.id = e.teacher;

CREATE VIEW v_promotions AS
  SELECT r.id, p.name_romaji AS person, r.dan, substr(r.date,1,4) AS year, d.name AS dojo
  FROM rank_events r JOIN persons p ON p.id = r.person LEFT JOIN dojos d ON d.id = r.dojo;

CREATE VIEW v_dojo AS
  SELECT d.id, d.name, d.loc_city, d.loc_region, d.loc_country,
         p.name_romaji AS chief_instructor, d.anchor, d.website
  FROM dojos d LEFT JOIN persons p ON p.id = d.chief_instructor;

CREATE VIEW v_tenure AS
  SELECT te.id, p.name_romaji AS person, d.name AS dojo, te.role, te.start, te.end, te.confidence
  FROM tenures te JOIN persons p ON p.id = te.person JOIN dojos d ON d.id = te.dojo;
"""


def _load(map_dir: Path, name: str) -> list[dict]:
    path = map_dir / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def _sources(cur, entity_type: str, rec: dict) -> None:
    cur.executemany("INSERT INTO sources VALUES (?,?,?)",
                    [(entity_type, rec["id"], u) for u in rec.get("source", [])])


def build_db(map_dir: str | Path, out_path: str | Path) -> dict:
    map_dir, out_path = Path(map_dir), Path(out_path)
    if out_path.exists():
        out_path.unlink()
    con = sqlite3.connect(out_path)
    cur = con.cursor()
    cur.executescript(SCHEMA)

    counts: dict[str, int] = {}

    persons = _load(map_dir, "persons")
    for p in persons:
        cr = p.get("current_rank") or {}
        cur.execute(
            "INSERT INTO persons VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (p["id"], p.get("name_romaji"), p.get("name_native"), p.get("born"), p.get("died"),
             int(bool(p.get("deceased"))), p.get("notes"), p.get("status"), p.get("retrieved"),
             cr.get("dan"), cr.get("title")))
        cur.executemany("INSERT INTO person_aliases VALUES (?,?)",
                        [(p["id"], a) for a in p.get("aliases", [])])
        _sources(cur, "person", p)
    counts["persons"] = len(persons)

    orgs = _load(map_dir, "organizations")
    for o in orgs:
        cur.execute("INSERT INTO organizations VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (o["id"], o.get("name"), o.get("abbrev"), o.get("type"), o.get("lineage"),
                     o.get("parent_org"), o.get("hq"), o.get("founded"), o.get("governance"),
                     o.get("website"), o.get("status"), o.get("retrieved")))
        _sources(cur, "organization", o)
    counts["organizations"] = len(orgs)

    dojos = _load(map_dir, "dojos")
    for d in dojos:
        loc = d.get("location") or {}
        cur.execute("INSERT INTO dojos VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (d["id"], d.get("name"), loc.get("city"), loc.get("region"), loc.get("country"),
                     d.get("chief_instructor"), d.get("founded"), int(bool(d.get("anchor"))),
                     d.get("website"), d.get("status"), d.get("retrieved")))
        cur.executemany("INSERT INTO dojo_orgs VALUES (?,?)", [(d["id"], o) for o in d.get("org", [])])
        cur.executemany("INSERT INTO dojo_instructors VALUES (?,?)",
                        [(d["id"], i) for i in d.get("instructors", [])])
        _sources(cur, "dojo", d)
    counts["dojos"] = len(dojos)

    rank_events = _load(map_dir, "rank_events")
    for r in rank_events:
        cur.execute("INSERT INTO rank_events VALUES (?,?,?,?,?,?,?,?,?)",
                    (r["id"], r.get("person"), r.get("dan"), r.get("title"), r.get("date"),
                     r.get("conferred_by"), r.get("via_org"), r.get("dojo"), r.get("retrieved")))
        _sources(cur, "rank_event", r)
    counts["rank_events"] = len(rank_events)

    tenures = _load(map_dir, "tenures")
    for t in tenures:
        cur.execute("INSERT INTO tenures VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (t["id"], t.get("person"), t.get("dojo"), t.get("role"), t.get("start"),
                     t.get("end"), t.get("confidence"), t.get("notes"), t.get("status"), t.get("retrieved")))
        _sources(cur, "tenure", t)
    counts["tenures"] = len(tenures)

    edges = _load(map_dir, "edges")
    for e in edges:
        cur.execute("INSERT INTO edges VALUES (?,?,?,?,?,?,?,?,?)",
                    (e["id"], e.get("student"), e.get("teacher"), e.get("kind"), e.get("period"),
                     e.get("confidence"), e.get("notes"), e.get("status"), e.get("retrieved")))
        _sources(cur, "edge", e)
    counts["edges"] = len(edges)

    con.commit()
    con.close()
    return counts


def main(argv: list[str] | None = None) -> int:
    import argparse

    repo_root = Path(__file__).resolve().parents[4]
    ap = argparse.ArgumentParser(prog="atr-crawler-db",
                                 description="Build a SQLite database from data/map JSON")
    ap.add_argument("--map-dir", type=Path, default=repo_root / "data" / "map")
    ap.add_argument("--out", type=Path, default=repo_root / "data" / "map" / "atr_map.sqlite")
    args = ap.parse_args(argv)
    counts = build_db(args.map_dir, args.out)
    print(f"Built {args.out}")
    for table, n in counts.items():
        print(f"  {table:14} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
