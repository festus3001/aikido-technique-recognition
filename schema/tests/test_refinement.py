"""Resolution cascade for the Refinement primitive: scope precedence + merge semantics."""

from schema.contribution import Provenance
from schema.refinement import RefinementStore, make_id, matching, resolve


def prov(date="2026-06-21", author="person:t", basis="teacher"):
    return Provenance(author=author, basis=basis, date=date)


def store(*refs):
    s = RefinementStore(path=None)   # in-memory only; never touches data/
    for level, target, payload, sel, p in refs:
        s.add(level, target, payload, p, selector=sel)
    return s


def test_override_narrowest_then_latest_wins():
    s = store(
        ("book", "caption", {"name_romaji": "from book"}, {"book": "v1"}, prov("2026-01-01")),
        ("page", "caption", {"name_romaji": "from page"}, {"book": "v1", "page": 5}, prov("2026-01-01")),
        ("page", "caption", {"name_romaji": "page newer"}, {"book": "v1", "page": 5}, prov("2026-02-01")),
    )
    # page scope beats book scope; among page scope the later date wins (upsert keeps one id anyway)
    got = resolve("caption", {"book": "v1", "page": 5}, s, base={"name_romaji": "seed"})
    assert got["name_romaji"] == "page newer"
    # a different page falls back to the book-scope refinement
    assert resolve("caption", {"book": "v1", "page": 9}, s, base=None)["name_romaji"] == "from book"
    # a different book falls back to the seed base
    assert resolve("caption", {"book": "v2", "page": 5}, s, base={"name_romaji": "seed"})["name_romaji"] == "seed"


def test_section_matches_by_page_range():
    s = store(
        ("book", "section", {"context": "aiki-jo", "kind": "suburi"}, {"book": "v1", "pages": [83, 123]}, prov()),
    )
    inside = resolve("section", {"book": "v1", "page": 100}, s, base={"context": "taijutsu"})
    assert inside["context"] == "aiki-jo"
    outside = resolve("section", {"book": "v1", "page": 60}, s, base={"context": "taijutsu"})
    assert outside["context"] == "taijutsu"   # falls back to seed


def test_additive_lexicon_union_onto_seed():
    s = store(
        ("process", "lexicon.entry", {"slot": "technique", "canonical": "koshi-nage", "variants": ["koshinage"]}, {}, prov()),
        ("book", "lexicon.entry", {"slot": "technique", "canonical": "kaiten-nage", "variants": ["kaitennage"]}, {"book": "v1"}, prov()),
    )

    def fold(base, payloads):
        out = {k: dict(v) for k, v in (base or {}).items()}
        for p in payloads:
            out.setdefault(p["slot"], {})[p["canonical"]] = p.get("variants", [])
        return out

    seed = {"technique": {"ikkyo": []}}
    got = resolve("lexicon.entry", {"book": "v1"}, s, base=seed, fold=fold)
    assert set(got["technique"]) == {"ikkyo", "koshi-nage", "kaiten-nage"}
    # a different book only sees the process-scope addition, not the v1 one
    got2 = resolve("lexicon.entry", {"book": "v2"}, s, base=seed, fold=fold)
    assert set(got2["technique"]) == {"ikkyo", "koshi-nage"}


def test_compose_returns_ordered_ops():
    s = store(
        ("page", "region.ops", {"op": "drop", "indices": [5]}, {"book": "v1", "page": 7}, prov("2026-01-01")),
        ("sequence", "region.ops", {"op": "merge", "indices": [0, 1]}, {"book": "v1", "page": 7, "seq": 1}, prov("2026-01-02")),
    )
    ops = resolve("region.ops", {"book": "v1", "page": 7, "seq": 1}, s, base=None)
    # page-scope op before sequence-scope op (broad -> narrow)
    assert [o["op"] for o in ops] == ["drop", "merge"]
    # at the page level (no seq) only the page-scope op matches
    ops_page = resolve("region.ops", {"book": "v1", "page": 7}, s, base=None)
    assert [o["op"] for o in ops_page] == ["drop"]


def test_retired_is_ignored_and_upsert_is_stable():
    s = store(("technique", "verdict", {"verdict": "confirmed"}, {"technique": "tech:a"}, prov()))
    rid = make_id_for(s, "tech:a")
    assert resolve("verdict", {"technique": "tech:a"}, s, base=None)["verdict"] == "confirmed"
    # re-adding the same scope+target upserts (one record), and retiring removes it from resolution
    s.add("technique", "verdict", {"verdict": "corrected"}, prov(), selector={"technique": "tech:a"})
    assert len([r for r in s.items if r.target == "verdict"]) == 1
    ref = s.by_target("verdict")[0]
    ref.status = "retired"
    s._reindex()
    assert resolve("verdict", {"technique": "tech:a"}, s, base="none") == "none"


def make_id_for(s, technique):
    from schema.refinement import Scope
    return make_id(Scope("technique", {"technique": technique}), "verdict")


def test_persistence_roundtrip(tmp_path):
    path = tmp_path / "refinements.json"
    s = RefinementStore(path=path)
    s.add("page", "caption", {"name_romaji": "x"}, prov(), selector={"book": "v1", "page": 3})
    s.save()
    again = RefinementStore(path=path)
    assert resolve("caption", {"book": "v1", "page": 3}, again, base=None)["name_romaji"] == "x"
