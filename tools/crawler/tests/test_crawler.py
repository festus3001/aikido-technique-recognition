"""Offline tests for the crawler core: slugs, idempotent merge, co-presence,
lineage parsing. No network or jsonschema required."""

import json
import sqlite3

from atr_crawler import copresence, db, dojo_sites, lineage, locators, reconcile, slugs, usaf, wikipedia
from atr_crawler.store import JsonStore, merge_record


# -- slugs -----------------------------------------------------------------

def test_normalize_strips_diacritics():
    assert slugs.normalize_romaji("Mōrihei") == "morihei"
    assert slugs.slugify("Yoshimitsu Yamada") == "yoshimitsu-yamada"


def test_entity_ids():
    assert slugs.person_id("Akira Tohei") == "person:akira-tohei"
    assert slugs.dojo_id("New York Aikikai") == "dojo:new-york-aikikai"
    assert slugs.edge_id("person:a-student", "person:a-teacher") == "edge:a-student+a-teacher"
    assert slugs.tenure_id("person:x", "dojo:y", "1960") == "tenure:x+y+1960"
    assert slugs.tenure_id("person:x", "dojo:y", None) == "tenure:x+y+unknown"


# -- store merge -----------------------------------------------------------

def test_merge_is_idempotent_and_unions_sources():
    a = {"id": "person:x", "name_romaji": "X", "source": ["u1"], "retrieved": "2026-01-01"}
    b = {"id": "person:x", "name_romaji": "X", "source": ["u2"], "retrieved": "2026-06-01",
         "name_native": "X native"}
    merged = merge_record(a, b)
    assert merged["source"] == ["u1", "u2"]
    assert merged["retrieved"] == "2026-06-01"
    assert merged["name_native"] == "X native"
    # idempotent: merging the same thing again changes nothing
    assert merge_record(merged, b) == merged


def test_null_never_erases_and_confidence_not_demoted():
    existing = {"id": "edge:a+b", "confidence": "stated", "notes": "kept", "source": ["u"]}
    incoming = {"id": "edge:a+b", "confidence": "inferred", "notes": None, "source": ["u"]}
    merged = merge_record(existing, incoming)
    assert merged["confidence"] == "stated"   # stated never demoted to inferred
    assert merged["notes"] == "kept"          # null does not erase


def test_store_upsert_dedupes_by_id(tmp_path):
    store = JsonStore(tmp_path)
    rec = {"id": "org:usaf", "name": "USAF", "source": ["u"], "retrieved": "2026-01-01"}
    store.upsert("organizations", rec)
    store.upsert("organizations", rec)
    assert store.count("organizations") == 1


# -- co-presence -----------------------------------------------------------

def _tenure(person, dojo, role, start, end, src="u", retrieved="2026-01-01"):
    return {"id": f"tenure:{person}+{dojo}+{start}", "person": f"person:{person}",
            "dojo": f"dojo:{dojo}", "role": role, "start": start, "end": end,
            "confidence": "inferred", "source": [src], "retrieved": retrieved}


def test_directional_overlap_makes_one_inferred_edge():
    tenures = [
        _tenure("ueshiba", "hombu", "founder", "1931", "1969"),
        _tenure("yamada", "hombu", "uchi-deshi", "1955", "1964"),
    ]
    result = copresence.derive_copresence(tenures)
    assert len(result["edges"]) == 1
    edge = result["edges"][0]
    assert edge["student"] == "person:yamada"
    assert edge["teacher"] == "person:ueshiba"
    assert edge["kind"] == "uchi-deshi"
    assert edge["confidence"] == "inferred"
    assert "co-presence" in edge["notes"]


def test_peer_overlap_records_pair_but_no_edge():
    tenures = [
        _tenure("yamada", "hombu", "uchi-deshi", "1955", "1964"),
        _tenure("kanai", "hombu", "uchi-deshi", "1959", "1966"),
    ]
    result = copresence.derive_copresence(tenures)
    assert result["edges"] == []
    assert len(result["pairs"]) == 1
    assert result["pairs"][0]["directional"] is False


def test_non_overlap_and_unknown_start_produce_nothing():
    disjoint = [
        _tenure("a", "d", "founder", "1931", "1950"),
        _tenure("b", "d", "uchi-deshi", "1960", "1969"),
    ]
    assert copresence.derive_copresence(disjoint)["pairs"] == []
    unknown = [
        _tenure("a", "d", "founder", "1931", "1969"),
        _tenure("b", "d", "uchi-deshi", None, "1969"),
    ]
    assert copresence.derive_copresence(unknown)["pairs"] == []


# -- lineage parsing -------------------------------------------------------

# -- USAF Kagamibiraki parser (Phase B) ------------------------------------

SAMPLE_USAF = """\
We are excited to announce the following New Year's promotions for 2023.
5th Dan:
Virginia Becart - Florida Aikikai
K. Hawk Durham - Evanston Aikido Center
Walter Braxton III - Aikido Schools of New Jersey
6th Dan:
George Hemmings - St Ives Aiki Dojo
Shihan:
Stephane Janczuk - Aikido la Forge
Stay tuned for more news - check back soon.
"""


def test_parse_usaf_dan_and_shihan():
    out = usaf.parse_kagamibiraki(SAMPLE_USAF, 2023, "2026-06-11")
    events = {e["id"]: e for e in out["rank_events"]}
    # five-dan and six-dan entries become rank_events; the footer line does not
    assert len(events) == 4
    becart = events["rank:virginia-becart+2023-01-01+5"]
    assert becart["dan"] == 5
    assert becart["date"] == "2023-01-01"
    assert becart["person"] == "person:virginia-becart"
    assert becart["dojo"] == "dojo:florida-aikikai"
    assert becart["via_org"] == "org:usaf"
    assert events["rank:george-hemmings+2023-01-01+6"]["dan"] == 6
    # Shihan confers a title, not a dan: a person, no rank_event
    assert "person:stephane-janczuk" in {p["id"] for p in out["persons"]}
    assert not any(e["person"] == "person:stephane-janczuk" for e in out["rank_events"])
    assert out["shihan_titles"] == ["person:stephane-janczuk"]


def test_parse_usaf_ignores_footer_and_intro():
    out = usaf.parse_kagamibiraki(SAMPLE_USAF, 2023, "2026-06-11")
    dojos = {d["id"] for d in out["dojos"]}
    assert "dojo:florida-aikikai" in dojos
    # "Stay tuned for more news - check back soon." must not become an entry
    assert not any("stay-tuned" in d for d in dojos)


# -- USAF dojo locator parser (Phase C) ------------------------------------

SAMPLE_LOCATOR = """\
<ul>
<li>
  <h3><a href="/dojos/new-york-aikikai/">New York Aikikai</a></h3>
  <dl>
    <dt>Chief Instructors</dt><dd>Yoshimitsu Yamada</dd><dd>Steve Sandage</dd>
    <dt>Main Address</dt><dd>142 W 18th St<br/>New York, NY 10011<br/>212-555-1234</dd>
    <dt>Website</dt><dd><a href="https://www.nyaikikai.com/">nyaikikai.com</a></dd>
  </dl>
</li>
<li>
  <h3><a href="/dojos/aikido-aruba/">Aikido Aruba</a></h3>
  <dl>
    <dt>Chief Instructors</dt><dd>Bryan Coffie</dd>
    <dt>Main Address</dt><dd>Tanki Leendert 59-A<br/>Noord,<br/>Aruba</dd>
  </dl>
</li>
</ul>
"""


def test_parse_usaf_locator():
    out = locators.parse_usaf_locator(SAMPLE_LOCATOR, "org:usaf", "2026-06-11",
                                      "https://services.usaikifed.com/dojos")
    dojos = {d["id"]: d for d in out["dojos"]}
    ny = dojos["dojo:new-york-aikikai"]
    assert ny["chief_instructor"] == "person:yoshimitsu-yamada"
    assert ny["instructors"] == ["person:steve-sandage"]
    assert ny["location"] == {"city": "New York", "region": "NY", "country": "USA"}
    assert ny["website"] == "https://www.nyaikikai.com/"
    assert ny["org"] == ["org:usaf"]
    # non-US address: city + country, no region
    aruba = dojos["dojo:aikido-aruba"]
    assert aruba["location"] == {"city": "Noord", "region": None, "country": "Aruba"}
    assert "person:bryan-coffie" in {p["id"] for p in out["persons"]}


def test_locator_dojo_id_matches_phase_b():
    # Phase C and Phase B must produce the same dojo id from the same name,
    # so locator data merges into promotion-list dojos.
    assert slugs.dojo_id("New York Aikikai") == "dojo:new-york-aikikai"


# -- Ki Society locator (Phase C) ------------------------------------------

KI_LISTING = """\
<ul>
<li><a href="https://ki-society.com/?dojo=ki-aikido-of-anderson-valley">Ki-Aikido of Anderson Valley</a></li>
<li><a href="/?dojo=chicago-ki-aikido">Chicago Ki Aikido</a></li>
</ul>
<div class="pagination">
<a href="https://ki-society.com/nation/usa/page/2/">2</a>
<a href="https://ki-society.com/nation/usa/page/3/">3</a>
</div>
"""

KI_DETAIL = """\
<p><a href="https://ki-society.com/nation/california/">CALIFORNIA</a> &gt;
   <a href="https://ki-society.com/nation/usa/">USA</a></p>
<table class="table table-striped">
  <tr><th>CHIEF INSTRUCTOR</th><td>Alex Korn</td></tr>
  <tr><th>Affiliation of Ki Society or Federation</th>
      <td><li><a href="https://ki-society.com/department/midland-ki-federation-mkf/">Midland Ki Federation (MKF)</a></li></td></tr>
  <tr><th>Webpage site address</th><td><a href="https://example-dojo.org/" target="_blank">site</a></td></tr>
</table>
"""


def test_kisociety_listing_and_pagination():
    entries = locators.parse_kisociety_listing(KI_LISTING)
    names = {e["name"] for e in entries}
    assert "Ki-Aikido of Anderson Valley" in names
    # relative href resolved to absolute
    assert any(e["url"] == "https://ki-society.com/?dojo=chicago-ki-aikido" for e in entries)
    assert locators.kisociety_max_page(KI_LISTING) == 3


def test_kisociety_detail():
    out = locators.parse_kisociety_detail(
        KI_DETAIL, "Ki-Aikido of Anderson Valley", "org:ki-society",
        "2026-06-11", "https://ki-society.com/?dojo=ki-aikido-of-anderson-valley")
    dojo = out["dojos"][0]
    assert dojo["chief_instructor"] == "person:alex-korn"
    assert dojo["location"] == {"city": None, "region": "California", "country": "USA"}
    assert dojo["website"] == "https://example-dojo.org/"
    assert "org:ki-society" in dojo["org"] and "org:midland-ki-federation" in dojo["org"]
    fed = out["orgs"][0]
    assert fed["id"] == "org:midland-ki-federation"
    assert fed["abbrev"] == "MKF" and fed["parent_org"] == "org:ki-society"
    assert "person:alex-korn" in {p["id"] for p in out["persons"]}


# -- AAA / AAI locator (Phase C) -------------------------------------------

AAA_DETAIL_US = """\
<div class="bde-div">
  <h1 class="bde-heading">Aikido of Shreveport</h1>
  <div class="bde-text">William R. Ross</div>
  <div class="bde-text"><a href="tel:(318) 469-1952">(318) 469-1952</a></div>
  <div class="bde-text"><a href="https://maps.app.goo.gl/x">447 North Market Street<br/>Shreveport, LA, 71107</a></div>
  <div class="bde-text"><a href="https://shreveportmartialarts.com">site</a></div>
  <div class="bde-text">Mission</div>
</div>
"""

AAA_DETAIL_INTL = """\
<h1 class="bde-heading">Aikido Bilbao</h1>
<div class="bde-text">Carlos Mendez</div>
<div class="bde-text"><a href="https://maps.app.goo.gl/y">Calle Mayor 1<br/>Bilbao<br/>Spain</a></div>
<div class="bde-text"><a href="https://aikidobilbao.es">site</a></div>
"""

AAA_LISTING = """\
<a href="https://aaa-aikido.com/dojo/aikido-of-shreveport/">Aikido of Shreveport</a>
<a href="/dojo/aikido-bilbao/">Aikido Bilbao</a>
<a href="https://aaa-aikido.com/dojos/">Find a dojo</a>
"""


def test_aaa_listing_skips_index():
    entries = locators.parse_aaa_listing(AAA_LISTING)
    urls = {e["url"] for e in entries}
    assert "https://aaa-aikido.com/dojo/aikido-of-shreveport/" in urls
    assert "https://aaa-aikido.com/dojo/aikido-bilbao/" in urls  # relative resolved
    assert "https://aaa-aikido.com/dojos/" not in urls  # the index link is not a dojo


def test_aaa_detail_us_routes_to_aaa():
    out = locators.parse_aaa_detail(AAA_DETAIL_US, "fallback", "2026-06-11",
                                    "https://aaa-aikido.com/dojo/aikido-of-shreveport/")
    dojo = out["dojos"][0]
    assert dojo["chief_instructor"] == "person:william-r-ross"
    assert dojo["location"] == {"city": "Shreveport", "region": "LA", "country": "USA"}
    assert dojo["website"] == "https://shreveportmartialarts.com"
    assert dojo["org"] == ["org:aaa"]


def test_aaa_detail_intl_routes_to_aai():
    out = locators.parse_aaa_detail(AAA_DETAIL_INTL, "Aikido Bilbao", "2026-06-11",
                                    "https://aaa-aikido.com/dojo/aikido-bilbao/")
    dojo = out["dojos"][0]
    assert dojo["org"] == ["org:aai"]
    assert dojo["location"]["country"] == "Spain"
    assert dojo["chief_instructor"] == "person:carlos-mendez"


# -- Shin Kaze locator (Phase C) -------------------------------------------

SHINKAZE_TABLE = """\
<table>
<tr><td></td><td></td><td class="D" width="20%">Dojo Name</td><td class="D">AIKIDO OAKVILLE</td></tr>
<tr><td></td><td></td><td class="D" width="20%">Chief Instructor</td><td class="D">Labeeb Zaatara</td></tr>
<tr><td></td><td></td><td class="D" width="20%">Address</td><td class="D">1033 North Service Rd. E,<br/>Oakville, ON L6H 1A1</td></tr>
<tr><td></td><td></td><td class="D" width="20%">Website</td><td class="D"><a href="https://www.facebook.com/AikidoOakville">fb</a></td></tr>
<tr><td class="S" colspan="4"></td></tr>
<tr><td></td><td></td><td class="D" width="20%">Dojo Name</td><td class="D">SHIN KAZE HONBU</td></tr>
<tr><td></td><td></td><td class="D" width="20%">Chief Instructor</td><td class="D">Akira Tohei and Jane Doe</td></tr>
</table>
"""


def test_parse_shinkaze_table():
    out = locators.parse_shinkaze(SHINKAZE_TABLE, "org:shin-kaze", "2026-06-11",
                                  "https://shinkazeaikidoalliance.com/home/dojos/")
    dojos = {d["id"]: d for d in out["dojos"]}
    oak = dojos["dojo:aikido-oakville"]
    assert oak["chief_instructor"] == "person:labeeb-zaatara"
    assert oak["location"] == {"city": "Oakville", "region": "ON", "country": "Canada"}
    assert oak["website"] == "https://www.facebook.com/AikidoOakville"
    assert oak["org"] == ["org:shin-kaze"]
    # co-instructors: first is chief, rest go to instructors
    honbu = dojos["dojo:shin-kaze-honbu"]
    assert honbu["chief_instructor"] == "person:akira-tohei"
    assert honbu["instructors"] == ["person:jane-doe"]


# -- Phase F reconcile -----------------------------------------------------

def _p(pid, name, **kw):
    return {"id": pid, "name_romaji": name, "source": ["u"], "retrieved": "2026-01-01", **kw}


def test_reconcile_tiers():
    persons = [
        _p("person:yoshimitsu-yamada", "Yoshimitsu Yamada"),
        _p("person:y-yamada", "Y. Yamada"),                      # medium: initial match
        _p("person:william-r-ross", "William R. Ross"),
        _p("person:william-ross", "William Ross"),               # high: middle initial only
        _p("person:john-smith", "John Smith"),
        _p("person:jane-smith", "Jane Smith"),                   # not a match (different first)
    ]
    out = reconcile.find_candidates(persons)
    high_members = {frozenset(c["members"]) for c in out["high"]}
    assert frozenset({"person:william-r-ross", "person:william-ross"}) in high_members
    # the fuller name is canonical
    ross = next(c for c in out["high"] if "person:william-ross" in c["members"])
    assert ross["canonical"] == "person:william-r-ross"
    medium_members = {frozenset(c["members"]) for c in out["medium"]}
    assert frozenset({"person:yoshimitsu-yamada", "person:y-yamada"}) in medium_members
    # John vs Jane Smith must not be flagged at all
    flagged = high_members | medium_members
    assert not any({"person:john-smith", "person:jane-smith"} <= s for s in flagged)


def test_reconcile_demotes_conflicting_cluster():
    # Plain "Andrew Demko" links two people with conflicting middle initials.
    # The whole cluster must be demoted to review, never auto-merged.
    persons = [
        _p("person:andrew-demko", "Andrew Demko"),
        _p("person:andrew-l-demko", "Andrew L. Demko"),
        _p("person:andrew-p-demko", "Andrew P. Demko"),
    ]
    out = reconcile.find_candidates(persons)
    assert out["high"] == []
    assert len(out["medium"]) == 1
    assert set(out["medium"][0]["members"]) == {
        "person:andrew-demko", "person:andrew-l-demko", "person:andrew-p-demko"}


def test_reconcile_native_name_is_high():
    persons = [
        _p("person:a", "Mitsugi Saotome", name_native="五月女 貢"),
        _p("person:b", "M. Saotome Sensei", name_native="五月女 貢"),
    ]
    out = reconcile.find_candidates(persons)
    assert any(set(c["members"]) == {"person:a", "person:b"} for c in out["high"])


def test_apply_merges_repoints_references(tmp_path):
    store = JsonStore(tmp_path)
    store.upsert("persons", _p("person:william-r-ross", "William R. Ross"))
    store.upsert("persons", _p("person:william-ross", "William Ross", name_native=None))
    # references to the soon-to-be-absorbed duplicate
    store.upsert("rank_events", {"id": "rank:william-ross+2023-01-01+5", "person": "person:william-ross",
                                 "dan": 5, "date": "2023-01-01", "source": ["u"], "retrieved": "2026-01-01"})
    store.upsert("dojos", {"id": "dojo:x", "name": "X", "chief_instructor": "person:william-ross",
                           "instructors": ["person:william-ross"], "source": ["u"], "retrieved": "2026-01-01"})

    out = reconcile.find_candidates(store.all("persons"))
    absorbed = reconcile.apply_merges(store, out["high"])
    assert absorbed == 1
    # duplicate person gone, canonical keeps the fuller name + gains an alias
    pids = {p["id"] for p in store.all("persons")}
    assert pids == {"person:william-r-ross"}
    canon = store.data["persons"]["person:william-r-ross"]
    assert "William Ross" in canon["aliases"]
    # rank_event re-pointed AND its id rewritten to the canonical slug
    ev = store.all("rank_events")[0]
    assert ev["person"] == "person:william-r-ross"
    assert ev["id"] == "rank:william-r-ross+2023-01-01+5"
    # dojo references re-pointed
    dojo = store.data["dojos"]["dojo:x"]
    assert dojo["chief_instructor"] == "person:william-r-ross"
    assert dojo["instructors"] == ["person:william-r-ross"]


# -- Phase D dojo-site extraction ------------------------------------------

def test_extract_instructors_signals():
    html = """
    <p>Chief Instructor: Jane A. Carter</p>
    <p>Our classes are led by Robert Smith Sensei.</p>
    <p>Assistant: David Lee, 4th dan.</p>
    <p>Welcome to Boston Aikikai, a great dojo.</p>
    """
    out = {r["name"]: r["role"] for r in dojo_sites.extract_instructors(html)}
    assert out["Jane A. Carter"] == "chief"
    assert out["Robert Smith"] == "instructor"
    assert out["David Lee"] == "instructor"
    # "Boston Aikikai" must not be taken as a person name
    assert not any("Aikikai" in n for n in out)


def test_extract_rejects_non_names():
    # signal words without a real full name nearby should yield nothing
    html = "<p>Our Sensei is welcoming. Aikido Dojo. Adult Classes.</p>"
    assert dojo_sites.extract_instructors(html) == []


def test_find_instructor_links_same_host_only():
    html = """
    <a href="/about/instructors/">Our Instructors</a>
    <a href="https://other.com/sensei">Sensei elsewhere</a>
    <a href="/schedule/">Schedule</a>
    """
    links = dojo_sites.find_instructor_links(html, "https://mydojo.org/")
    assert "https://mydojo.org/about/instructors/" in links
    assert all("other.com" not in u for u in links)  # off-host link skipped


# -- Phase E Wikipedia infobox (live extraction) ---------------------------

def _ib(rows: str) -> str:
    return f'<table class="infobox vcard"><tbody>{rows}</tbody></table>'


WIKI_HTML = _ib(
    '<tr><th>Born</th><td><a href="/wiki/Shinjuku,_Tokyo">Shinjuku, Tokyo</a></td></tr>'
    '<tr><th>Teacher</th><td><a href="/wiki/Morihei_Ueshiba">Morihei Ueshiba</a></td></tr>'
    '<tr><th>Notable students</th><td>'
    '<a href="/wiki/Terada_Kiyoyuki">Kiyoyuki Terada</a>, '
    '<a href="/wiki/Takashi_Kushida">Takashi Kushida</a>, '
    '<a href="/wiki/List_of_aikidoka">List of aikidoka</a></td></tr>'
    '<tr><th>Rank</th><td>9th dan Aikikai</td></tr>'
) + '<span lang="ja">塩田 剛三</span>'


def test_parse_infobox_html_fields():
    info = wikipedia.parse_infobox_html(WIKI_HTML)
    assert info["teachers"] == ["Morihei Ueshiba"]
    assert info["students"] == ["Terada Kiyoyuki", "Takashi Kushida"]  # "List of aikidoka" filtered
    assert info["dan"] == 9
    # the Born row's birthplace link must NOT be treated as a teacher/student
    assert "Shinjuku, Tokyo" not in info["teachers"] + info["students"]


def test_is_aikido_article_guard():
    aikido = _ib('<tr><th>Style</th><td>Aikido</td></tr>')
    karate = _ib('<tr><th>Style</th><td>Shotokan Karate</td></tr>') + \
        '<a href="/wiki/Category:Japanese_karateka">cat</a>'
    assert wikipedia.is_aikido_article(aikido) is True
    assert wikipedia.is_aikido_article(karate) is False


def test_wikipedia_crawl_stops_at_non_aikido():
    # an aikidoka who cross-trained links to a karate master; the karate master's
    # own students must NOT be pulled in (no domain drift).
    pages = {
        "Aikido_Teacher": _ib('<tr><th>Style</th><td>Aikido</td></tr>'
                              '<tr><th>Notable students</th><td><a href="/wiki/Karate_Master">KM</a></td></tr>'),
        "Karate_Master": _ib('<tr><th>Style</th><td>Shotokan Karate</td></tr>'
                             '<tr><th>Notable students</th><td><a href="/wiki/Karate_Kid">KK</a></td></tr>'),
    }

    class FakeFetcher:
        def get(self, url, refresh=False):
            return pages.get(url.split("/wiki/", 1)[1]) if "/wiki/" in url else None

    out = wikipedia.crawl_wikipedia(FakeFetcher(), "2026-06-11", max_articles=10, seeds=["Aikido Teacher"])
    pids = {p["id"] for p in out["persons"]}
    # the boundary karate master is recorded (referenced by the aikido article)...
    assert "person:karate-master" in pids
    # ...but his karate student was never pulled in
    assert "person:karate-kid" not in pids
    eids = {e["id"] for e in out["edges"]}
    assert "edge:karate-master+aikido-teacher" in eids   # boundary edge kept
    assert not any("karate-kid" in e for e in eids)       # no drift edge


def test_wikipedia_crawl_bfs():
    aikido = '<tr><th>Style</th><td>Aikido</td></tr>'
    pages = {
        "Gozo_Shioda": _ib(aikido + '<tr><th>Teacher</th><td><a href="/wiki/Morihei_Ueshiba">U</a></td></tr>'
                           '<tr><th>Notable students</th><td><a href="/wiki/Takashi_Kushida">K</a></td></tr>'
                           '<tr><th>Rank</th><td>9th dan</td></tr>'),
        "Morihei_Ueshiba": _ib(aikido + '<tr><th>Notable students</th><td>'
                               '<a href="/wiki/Gozo_Shioda">S</a>, <a href="/wiki/Koichi_Tohei">T</a></td></tr>'),
        "Takashi_Kushida": _ib(aikido + '<tr><th>Teacher</th><td><a href="/wiki/Gozo_Shioda">S</a></td></tr>'),
        "Koichi_Tohei": _ib(aikido + '<tr><th>Teacher</th><td><a href="/wiki/Morihei_Ueshiba">U</a></td></tr>'),
    }

    class FakeFetcher:
        def get(self, url, refresh=False):
            return pages.get(url.split("/wiki/", 1)[1]) if "/wiki/" in url else None

    out = wikipedia.crawl_wikipedia(FakeFetcher(), "2026-06-11", max_articles=10, seeds=["Gozo Shioda"])
    eids = {e["id"] for e in out["edges"]}
    assert "edge:gozo-shioda+morihei-ueshiba" in eids       # Shioda <- Ueshiba
    assert "edge:takashi-kushida+gozo-shioda" in eids       # Kushida <- Shioda
    assert all(e["confidence"] == "stated" for e in out["edges"])
    pids = {p["id"] for p in out["persons"]}
    assert {"person:gozo-shioda", "person:morihei-ueshiba", "person:koichi-tohei"} <= pids


# -- SQLite migration ------------------------------------------------------

def test_build_db_and_views(tmp_path):
    mapdir = tmp_path / "map"
    mapdir.mkdir()
    (mapdir / "persons.json").write_text(json.dumps([
        {"id": "person:teacher", "name_romaji": "The Teacher", "aliases": ["T. Teacher"],
         "current_rank": {"dan": 8, "title": "shihan"}, "source": ["u1"], "retrieved": "2026-01-01"},
        {"id": "person:student", "name_romaji": "A Student", "source": ["u2"], "retrieved": "2026-01-01"},
    ]))
    (mapdir / "dojos.json").write_text(json.dumps([
        {"id": "dojo:x", "name": "X Dojo", "location": {"city": "Town", "region": "ST", "country": "USA"},
         "chief_instructor": "person:teacher", "org": ["org:y"], "instructors": ["person:student"],
         "source": ["u3"], "retrieved": "2026-01-01"},
    ]))
    (mapdir / "edges.json").write_text(json.dumps([
        {"id": "edge:student+teacher", "student": "person:student", "teacher": "person:teacher",
         "kind": "uchi-deshi", "confidence": "stated", "source": ["u4"], "retrieved": "2026-01-01"},
    ]))
    for empty in ("organizations", "rank_events", "tenures"):
        (mapdir / f"{empty}.json").write_text("[]")

    out = tmp_path / "map.sqlite"
    counts = db.build_db(mapdir, out)
    assert counts["persons"] == 2 and counts["edges"] == 1

    con = sqlite3.connect(out)
    # the readable lineage view joins ids to names
    row = con.execute("SELECT student, teacher, confidence FROM v_lineage").fetchone()
    assert row == ("A Student", "The Teacher", "stated")
    # nested current_rank flattened to columns
    dan = con.execute("SELECT current_rank_dan FROM persons WHERE id='person:teacher'").fetchone()[0]
    assert dan == 8
    # list fields became child tables
    assert con.execute("SELECT alias FROM person_aliases").fetchone()[0] == "T. Teacher"
    assert con.execute("SELECT count(*) FROM dojo_instructors").fetchone()[0] == 1
    assert con.execute("SELECT count(*) FROM sources").fetchone()[0] == 4
    con.close()


def test_parse_lineage_arrow_edges(tmp_path):
    f = tmp_path / "lineage.md"
    f.write_text(
        "- **Aikido Journal -- chart** something\n"
        "  - Gozo Shioda (Yoshinkan) -> Terada, Kushida, Y. Shioda\n",
        encoding="utf-8",
    )
    parsed = lineage.parse_lineage_sources(f, "2026-06-11")
    eids = {e["id"] for e in parsed["edges"]}
    assert "edge:terada+gozo-shioda" in eids
    assert all(e["confidence"] == "stated" for e in parsed["edges"])
    pids = {p["id"] for p in parsed["persons"]}
    assert "person:gozo-shioda" in pids and "person:y-shioda" in pids
    assert parsed["registry"]  # the bolded prose source was registered
