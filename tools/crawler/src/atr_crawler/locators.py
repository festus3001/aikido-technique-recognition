"""Phase C parser: federation dojo locators.

Walks a federation's dojo directory into `dojo` records (linked to the org) and
captures chief/assistant instructors as `person` records. Dojo ids are derived
from the dojo name via the same slug as Phase B, so locator data merges into and
enriches the dojos already created from promotion lists -- filling in chief
instructor, location, and website.

USAF locator (services.usaikifed.com/dojos): a static page, one <li> per dojo:

    <li>
      <h3><a href="/dojos/<slug>/">New York Aikikai</a></h3>
      <dl>
        <dt>Chief Instructors</dt><dd>Yoshimitsu Yamada</dd> ...
        <dt>Main Address</dt><dd>street<br/>City, ST 10001<br/>phone</dd>
        <dt>Website</dt><dd><a href="...">...</a></dd>
      </dl>
    </li>

Other federation locators (Ki Society, AAA/AAI, Shin Kaze) are registered in
LOCATORS but not yet given parsers; Phase C logs them as pending rather than
inventing structure it has not inspected.
"""

from __future__ import annotations

import re

from .slugs import dojo_id, org_id, person_id

# Federation locators. crawl=None means registered-but-not-yet-implemented.
LOCATORS = [
    {"org": "org:usaf", "url": "https://services.usaikifed.com/dojos", "crawl": "usaf"},
    {"org": "org:ki-society", "url": "https://ki-society.com/nation/usa/", "crawl": "kisociety"},
    {"org": "org:aaa", "url": "https://aaa-aikido.com/dojos/", "crawl": "aaa"},
    {"org": "org:shin-kaze", "url": "https://shinkazeaikidoalliance.com/home/dojos/", "crawl": "shinkaze"},
]

_PHONE = re.compile(r"^[\d().+\-\s]{7,}$")
_US_CITY_STATE = re.compile(r"^(.+?),\s*([A-Z]{2})(?:\s+\d{5}(?:-\d{4})?)?$")


def _address_lines(dd) -> list[str]:
    for br in dd.find_all("br"):
        br.replace_with("\n")
    return [ln.strip() for ln in dd.get_text("\n").split("\n") if ln.strip()]


def _parse_location(dd) -> dict | None:
    lines = [ln for ln in _address_lines(dd) if not _PHONE.match(ln)]
    city = region = country = None
    for ln in lines:
        m = _US_CITY_STATE.match(ln)
        if m:
            city, region, country = m.group(1).strip(), m.group(2), "USA"
            break
    if city is None:
        # Non-US form: "City," on one line, country on the next.
        commas = [ln for ln in lines if ln.endswith(",")]
        if commas:
            city = commas[0].rstrip(",").strip()
            idx = lines.index(commas[0])
            if idx + 1 < len(lines):
                country = lines[idx + 1].strip()
    if not any((city, region, country)):
        return None
    return {"city": city, "region": region, "country": country}


def _labelled_dds(dl) -> dict[str, list]:
    out: dict[str, list] = {}
    current = None
    for child in dl.find_all(["dt", "dd"], recursive=False):
        if child.name == "dt":
            current = child.get_text(strip=True).lower()
            out.setdefault(current, [])
        elif current is not None:
            out[current].append(child)
    return out


def parse_usaf_locator(html: str, org: str, retrieved: str, source_url: str) -> dict:
    """Parse the USAF dojo locator into dojo + person records."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    source = [source_url]
    dojos: dict[str, dict] = {}
    persons: dict[str, dict] = {}

    for h3 in soup.find_all("h3"):
        link = h3.find("a", href=re.compile(r"^/dojos/[^/]+/?$"))
        if not link:
            continue
        name = link.get_text(strip=True)
        if not name:
            continue
        li = h3.find_parent("li")
        dl = li.find("dl") if li else None
        labels = _labelled_dds(dl) if dl else {}

        # Instructors: dds under the "Chief Instructor(s)" label.
        instr_names: list[str] = []
        for label, dds in labels.items():
            if label.startswith("chief") or label == "instructors":
                instr_names = [d.get_text(strip=True) for d in dds if d.get_text(strip=True)]
                break
        instr_ids: list[str] = []
        for iname in instr_names:
            pid = person_id(iname)
            persons.setdefault(pid, {
                "id": pid, "name_romaji": iname, "source": list(source),
                "retrieved": retrieved, "status": "provisional",
            })
            instr_ids.append(pid)

        location = None
        for label, dds in labels.items():
            if "address" in label and dds:
                location = _parse_location(dds[0])
                break

        website = None
        for label, dds in labels.items():
            if label == "website" and dds:
                a = dds[0].find("a", href=True)
                website = a["href"] if a else (dds[0].get_text(strip=True) or None)
                break

        did = dojo_id(name)
        dojos[did] = {
            "id": did, "name": name, "org": [org],
            "location": location,
            "chief_instructor": instr_ids[0] if instr_ids else None,
            "instructors": instr_ids[1:],
            "website": website,
            "source": list(source), "retrieved": retrieved, "status": "provisional",
        }

    return {"dojos": list(dojos.values()), "persons": list(persons.values()), "orgs": []}


def crawl_usaf(fetcher, org: str, url: str, retrieved: str) -> dict:
    html = fetcher.get(url)
    if not html:
        return {"dojos": [], "persons": [], "orgs": []}
    return parse_usaf_locator(html, org, retrieved, url)


# -- Ki Society (Shinshin Toitsu Aikido) -----------------------------------
# WordPress site: a paginated USA listing of <li><a href="?dojo=slug">Name</a>,
# with per-dojo detail pages carrying chief instructor, federation affiliation,
# state (breadcrumb), and website in a <table>.

_KI_DETAIL = re.compile(r"\?dojo=")
_KI_PAGE = re.compile(r"/nation/usa/page/(\d+)")
_KI_STATE = re.compile(r"/nation/([a-z-]+)/?$", re.I)
_KI_DEPT = re.compile(r"/department/([a-z0-9-]+)/?$", re.I)


def parse_kisociety_listing(html: str, base_url: str = "https://ki-society.com") -> list[dict]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    seen: dict[str, dict] = {}
    for a in soup.find_all("a", href=_KI_DETAIL):
        name = a.get_text(strip=True)
        href = a["href"]
        if not name:
            continue
        if href.startswith("/"):
            href = base_url + href
        seen.setdefault(href, {"name": name, "url": href})
    return list(seen.values())


def kisociety_max_page(html: str) -> int:
    pages = [int(m.group(1)) for m in _KI_PAGE.finditer(html)]
    return max(pages) if pages else 1


def _table_rows(soup) -> dict[str, "object"]:
    rows: dict[str, object] = {}
    for tr in soup.find_all("tr"):
        th, td = tr.find("th"), tr.find("td")
        if th and td:
            rows.setdefault(th.get_text(strip=True).lower(), td)
    return rows


def parse_kisociety_detail(html: str, name: str, org: str, retrieved: str, source_url: str) -> dict:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    source = [source_url]
    rows = _table_rows(soup)
    persons: list[dict] = []
    orgs: list[dict] = []
    org_ids = [org]

    chief_id = None
    for label, td in rows.items():
        if "chief instructor" in label:
            chief = td.get_text(strip=True)
            if chief:
                chief_id = person_id(chief)
                persons.append({"id": chief_id, "name_romaji": chief, "source": list(source),
                                "retrieved": retrieved, "status": "provisional"})
            break

    for label, td in rows.items():
        if "affiliation" in label:
            a = td.find("a", href=_KI_DEPT)
            if a:
                fed_name = a.get_text(strip=True)
                abbrev = None
                m = re.search(r"\(([^)]+)\)", fed_name)
                if m:
                    abbrev = m.group(1)
                oid = org_id(re.sub(r"\s*\([^)]*\)", "", fed_name).strip())
                # Only the named US federations are federations; the rest are
                # regional societies the affiliation field happens to list.
                otype = "federation" if "federation" in fed_name.lower() else "association"
                orgs.append({"id": oid, "name": fed_name, "abbrev": abbrev, "type": otype,
                             "lineage": "ki-society", "parent_org": "org:ki-society",
                             "website": a["href"], "source": list(source),
                             "retrieved": retrieved, "status": "provisional"})
                org_ids.append(oid)
            break

    website = None
    for label, td in rows.items():
        if "webpage" in label or "website" in label:
            a = td.find("a", href=True)
            if a and a["href"].strip():
                website = a["href"].strip()
            break

    # State from the breadcrumb: a /nation/<state>/ link that is not USA.
    region = None
    for a in soup.find_all("a", href=_KI_STATE):
        m = _KI_STATE.search(a["href"])
        slug = m.group(1).lower()
        if slug != "usa":
            region = a.get_text(strip=True).title()
            break
    location = {"city": None, "region": region, "country": "USA"} if region else None

    did = dojo_id(name)
    dojo = {"id": did, "name": name, "org": org_ids, "location": location,
            "chief_instructor": chief_id, "instructors": [], "website": website,
            "source": list(source), "retrieved": retrieved, "status": "provisional"}
    return {"dojos": [dojo], "persons": persons, "orgs": orgs}


def crawl_kisociety(fetcher, org: str, url: str, retrieved: str) -> dict:
    first = fetcher.get(url)
    if not first:
        return {"dojos": [], "persons": [], "orgs": []}
    listing = parse_kisociety_listing(first)
    base = url.rstrip("/")
    for page in range(2, kisociety_max_page(first) + 1):
        more = fetcher.get(f"{base}/page/{page}/")
        if more:
            listing += parse_kisociety_listing(more)

    dojos: dict[str, dict] = {}
    persons: dict[str, dict] = {}
    orgs: dict[str, dict] = {}
    for entry in {d["url"]: d for d in listing}.values():
        detail = fetcher.get(entry["url"])
        if not detail:
            continue
        parsed = parse_kisociety_detail(detail, entry["name"], org, retrieved, entry["url"])
        for d in parsed["dojos"]:
            dojos[d["id"]] = d
        for p in parsed["persons"]:
            persons.setdefault(p["id"], p)
        for o in parsed["orgs"]:
            orgs.setdefault(o["id"], o)
    return {"dojos": list(dojos.values()), "persons": list(persons.values()), "orgs": list(orgs.values())}


# -- Aikido Association of America / International --------------------------
# WordPress (Breakdance builder). A single /dojos/ listing of /dojo/<slug>/
# links; each detail page has a contact block where the FIRST plain-text div is
# the chief instructor, followed by tel / email / maps-address / website links.
# US dojos belong to AAA; non-US ones to its international body AAI.

_AAA_DETAIL = re.compile(r"/dojo/[^/]+/?$")
_AAA_CITY = re.compile(r"^([A-Za-z][A-Za-z .'\-]*),\s*([A-Z]{2})(?:,?\s*\d{5}(?:-\d{4})?)?$")
_AAA_STATE = re.compile(r",\s*([A-Z]{2})(?:,?\s*\d{5})")
_MAPS = re.compile(r"maps\.(app\.)?goo|google\.com/maps", re.I)
_NAME_OK = re.compile(r"^[A-Z][A-Za-z.'\-]*(?:\s+[A-Za-z.'\-]+){0,4}$")


def _clean_paren(text: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", text).strip()


def _br_lines(node) -> list[str]:
    for br in node.find_all("br"):
        br.replace_with("\n")
    return [ln.strip() for ln in node.get_text("\n").split("\n") if ln.strip()]


def _parse_aaa_address(node) -> dict | None:
    lines = _br_lines(node)
    for ln in lines:
        m = _AAA_CITY.match(ln)
        if m:
            return {"city": m.group(1).strip(), "region": m.group(2), "country": "USA"}
    for ln in lines:
        m = _AAA_STATE.search(ln)
        if m:
            return {"city": None, "region": m.group(1), "country": "USA"}
    # Non-US (AAI): no US state; take the last line as country if it looks like one.
    if lines and lines[-1].replace(" ", "").isalpha() and len(lines[-1]) <= 30:
        return {"city": None, "region": None, "country": lines[-1]}
    return None


def parse_aaa_listing(html: str, base_url: str = "https://aaa-aikido.com") -> list[dict]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    seen: dict[str, dict] = {}
    for a in soup.find_all("a", href=_AAA_DETAIL):
        name = a.get_text(strip=True)
        if not name:
            continue
        href = a["href"]
        if href.startswith("/"):
            href = base_url + href
        seen.setdefault(href, {"name": name, "url": href})
    return list(seen.values())


def parse_aaa_detail(html: str, name: str, retrieved: str, source_url: str) -> dict:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    source = [source_url]
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        name = h1.get_text(strip=True)

    texts = soup.select(".bde-text")
    chief_id = None
    persons: list[dict] = []
    location = None
    website = None

    for td in texts:
        if td.find("a"):
            continue
        candidate = _clean_paren(td.get_text(" ", strip=True))
        if candidate and _NAME_OK.match(candidate):
            chief_id = person_id(candidate)
            persons.append({"id": chief_id, "name_romaji": candidate, "source": list(source),
                            "retrieved": retrieved, "status": "provisional"})
            break

    for td in texts:
        a = td.find("a", href=True)
        if not a:
            continue
        href = a["href"]
        if _MAPS.search(href) and location is None:
            location = _parse_aaa_address(td)
        elif href.startswith("http") and not _MAPS.search(href) and website is None:
            website = href

    org = "org:aaa" if (location is None or location.get("country") == "USA") else "org:aai"
    did = dojo_id(name)
    dojo = {"id": did, "name": name, "org": [org], "location": location,
            "chief_instructor": chief_id, "instructors": [], "website": website,
            "source": list(source), "retrieved": retrieved, "status": "provisional"}
    return {"dojos": [dojo], "persons": persons, "orgs": []}


def crawl_aaa(fetcher, org: str, url: str, retrieved: str) -> dict:
    listing_html = fetcher.get(url)
    if not listing_html:
        return {"dojos": [], "persons": [], "orgs": []}
    dojos: dict[str, dict] = {}
    persons: dict[str, dict] = {}
    for entry in parse_aaa_listing(listing_html):
        detail = fetcher.get(entry["url"])
        if not detail:
            continue
        parsed = parse_aaa_detail(detail, entry["name"], retrieved, entry["url"])
        for d in parsed["dojos"]:
            dojos[d["id"]] = d
        for p in parsed["persons"]:
            persons.setdefault(p["id"], p)
    return {"dojos": list(dojos.values()), "persons": list(persons.values()), "orgs": []}


# -- Shin Kaze Aikido Alliance ---------------------------------------------
# WordPress, but the dojo list is one big HTML <table>: each dojo is a run of
# label/value rows (Dojo Name, Chief Instructor, Address, Phone, Email, Website)
# in td.D cells, dojos separated by spacer rows. One page, no detail pages.

_SK_LABELS = {"dojo name", "chief instructor", "address", "phone", "email", "website"}
_CA_PROV = {"ON", "QC", "BC", "AB", "MB", "SK", "NS", "NB", "NL", "PE", "NT", "YT", "NU"}
_CITY_REGION = re.compile(r"([A-Za-z][A-Za-z .'\-]+),\s*([A-Z]{2})\b")


def _loc_from_text(text: str) -> dict | None:
    m = _CITY_REGION.search(text)
    if not m:
        return None
    region = m.group(2)
    country = "Canada" if region in _CA_PROV else ("USA" if region.isalpha() else None)
    return {"city": m.group(1).strip(), "region": region, "country": country}


def _split_instructors(text: str) -> list[str]:
    parts = re.split(r"\s*(?:,| and | & )\s*", text)
    return [p.strip() for p in parts if p.strip()]


def parse_shinkaze(html: str, org: str, retrieved: str, source_url: str) -> dict:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    source = [source_url]

    records: list[dict] = []
    current: dict | None = None
    for tr in soup.find_all("tr"):
        dcells = [td for td in tr.find_all("td") if "D" in (td.get("class") or [])]
        label = value_td = None
        for i, td in enumerate(dcells):
            txt = td.get_text(" ", strip=True).lower()
            if txt in _SK_LABELS:
                label = txt
                value_td = dcells[i + 1] if i + 1 < len(dcells) else None
                break
        if label is None:
            continue
        if label == "dojo name":
            if current and current.get("name"):
                records.append(current)
            current = {"name": value_td.get_text(" ", strip=True) if value_td else None}
        elif current is not None and value_td is not None:
            current[label] = value_td
    if current and current.get("name"):
        records.append(current)

    dojos: dict[str, dict] = {}
    persons: dict[str, dict] = {}
    for rec in records:
        name = rec.get("name")
        if not name:
            continue
        chief_id = None
        instr_ids: list[str] = []
        chief_td = rec.get("chief instructor")
        if chief_td is not None:
            for iname in _split_instructors(chief_td.get_text(" ", strip=True)):
                pid = person_id(iname)
                persons.setdefault(pid, {"id": pid, "name_romaji": iname, "source": list(source),
                                         "retrieved": retrieved, "status": "provisional"})
                instr_ids.append(pid)
            if instr_ids:
                chief_id = instr_ids[0]
        location = None
        if rec.get("address") is not None:
            location = _loc_from_text("\n".join(_br_lines(rec["address"])))
        website = None
        if rec.get("website") is not None:
            a = rec["website"].find("a", href=True)
            if a:
                website = a["href"].strip()
        did = dojo_id(name)
        dojos[did] = {"id": did, "name": name, "org": [org], "location": location,
                      "chief_instructor": chief_id, "instructors": instr_ids[1:],
                      "website": website, "source": list(source),
                      "retrieved": retrieved, "status": "provisional"}
    return {"dojos": list(dojos.values()), "persons": list(persons.values()), "orgs": []}


def crawl_shinkaze(fetcher, org: str, url: str, retrieved: str) -> dict:
    html = fetcher.get(url)
    if not html:
        return {"dojos": [], "persons": [], "orgs": []}
    return parse_shinkaze(html, org, retrieved, url)


CRAWLERS = {"usaf": crawl_usaf, "kisociety": crawl_kisociety, "aaa": crawl_aaa,
            "shinkaze": crawl_shinkaze}
