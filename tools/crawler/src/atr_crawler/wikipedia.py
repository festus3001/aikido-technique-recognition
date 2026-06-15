"""Phase E live extraction: lineage edges from Wikipedia infoboxes.

The lineage source registry (lineage_seed_sources.md) names "Wikipedia per-teacher
infoboxes" as a source. Each aikidoka article's infobox has a `Teacher` row and a
`Notable students` row of wikilinks; the article stating the link is the source,
so these edges are tagged `stated`. From a set of seed teachers this does a
bounded breadth-first crawl over the teacher/student links, building the lineage
graph, and reads `Rank` (dan) and the Japanese name to enrich person records.

Wikipedia's robots.txt disallows the /w/ action API but allows /wiki/ article
pages, so this parses the article HTML infobox. Only links inside the Teacher and
Notable-students rows are followed -- the Born row links to a birthplace, not a
person. Edges and persons enter as `status: provisional`.
"""

from __future__ import annotations

import re
from urllib.parse import unquote

from .slugs import person_id, edge_id, slugify

ARTICLE = "https://en.wikipedia.org/wiki/{title}"

SEED_TEACHERS = [
    "Morihei Ueshiba", "Kisshomaru Ueshiba", "Moriteru Ueshiba", "Koichi Tohei",
    "Gozo Shioda", "Morihiro Saito", "Nobuyoshi Tamura", "Mitsugi Saotome",
    "Hiroshi Tada", "Kazuo Chiba", "Yoshimitsu Yamada", "Mitsunari Kanai",
    "Seiichi Sugano", "Kenji Tomiki", "Minoru Mochizuki", "Kisaburo Osawa",
    "Rinjiro Shirata", "Shoji Nishio", "Yoshio Sugino",
]

_WIKI_HREF = re.compile(r"^/wiki/[^:]+$")  # article links only (no File:/Category:/etc.)

# Titles that appear in teacher/student rows but are not people.
_NOT_PERSON = {"aikido", "aikikai", "yoshinkan", "ki society", "ki-aikido",
               "daito-ryu aiki-jujutsu", "daito-ryu", "aikikai foundation"}


def _is_person_title(title: str) -> bool:
    low = title.lower()
    if low.startswith("list of") or low.startswith("aikido "):
        return False
    return slugify(title) not in {slugify(x) for x in _NOT_PERSON}


def article_url(title: str) -> str:
    return ARTICLE.format(title=title.strip().replace(" ", "_"))


def _title_from_href(href: str) -> str:
    return unquote(href.split("/wiki/", 1)[1]).replace("_", " ").split("#")[0].strip()


def _dan(text: str) -> int | None:
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s*dan", text, re.I)
    if m:
        n = int(m.group(1))
        return n if 1 <= n <= 10 else None
    return None


def is_aikido_article(html: str) -> bool:
    """True if the article is about aikido -- its infobox Style/Martial-art row
    or one of its categories mentions aikido. Used to stop the crawl from
    expanding into adjacent arts (karate, judo) via cross-discipline teachers."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    ib = soup.find("table", class_=re.compile(r"infobox"))
    if ib:
        for tr in ib.find_all("tr"):
            th, td = tr.find("th"), tr.find("td")
            if th and td and re.search(r"style|martial art|discipline", th.get_text(" ", strip=True), re.I):
                if "aikido" in td.get_text(" ", strip=True).lower():
                    return True
    for a in soup.find_all("a", href=re.compile(r"/wiki/Category:")):
        if "aikido" in a["href"].lower():
            return True
    return False


def parse_infobox_html(html: str) -> dict:
    """Extract teacher/student article titles plus native name and dan."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    ib = soup.find("table", class_=re.compile(r"infobox"))
    if ib is None:
        return {"teachers": [], "students": [], "native_name": None, "dan": None}

    teachers: list[str] = []
    students: list[str] = []
    dan = None
    for tr in ib.find_all("tr"):
        th, td = tr.find("th"), tr.find("td")
        if not (th and td):
            continue
        label = th.get_text(" ", strip=True).lower()
        if "teacher" in label:
            teachers += [t for a in td.find_all("a", href=_WIKI_HREF)
                         if _is_person_title(t := _title_from_href(a["href"]))]
        elif "student" in label:
            students += [t for a in td.find_all("a", href=_WIKI_HREF)
                         if _is_person_title(t := _title_from_href(a["href"]))]
        elif "rank" in label:
            dan = _dan(td.get_text(" ", strip=True))

    ja = ib.find("span", attrs={"lang": "ja"})
    native = ja.get_text(strip=True) if ja else None
    return {
        "teachers": list(dict.fromkeys(teachers)),
        "students": list(dict.fromkeys(students)),
        "native_name": native,
        "dan": dan,
    }


def crawl_wikipedia(fetcher, retrieved: str, max_articles: int = 80,
                    seeds: list[str] | None = None) -> dict:
    """Bounded BFS over Wikipedia aikidoka infoboxes. Returns {persons, edges}."""
    seeds = seeds or SEED_TEACHERS
    queue = list(seeds)
    visited: set = set()
    persons: dict[str, dict] = {}
    edges: dict[str, dict] = {}

    def add_person(name: str, source: str, native=None, dan=None) -> str:
        pid = person_id(name)
        rec = persons.get(pid)
        if rec is None:
            rec = {"id": pid, "name_romaji": name, "source": [source],
                   "retrieved": retrieved, "status": "provisional"}
            persons[pid] = rec
        elif source not in rec["source"]:
            rec["source"].append(source)
        if native and not rec.get("name_native"):
            rec["name_native"] = native
        if dan and not rec.get("current_rank"):
            rec["current_rank"] = {"dan": dan, "title": None}
        return pid

    def add_edge(student_name: str, teacher_name: str, source: str, note: str) -> None:
        sid, tid = person_id(student_name), person_id(teacher_name)
        if sid == tid:
            return
        eid = edge_id(sid, tid)
        if eid in edges:
            if source not in edges[eid]["source"]:
                edges[eid]["source"].append(source)
            return
        edges[eid] = {"id": eid, "student": sid, "teacher": tid, "kind": "direct-student",
                      "period": None, "confidence": "stated", "notes": note,
                      "source": [source], "retrieved": retrieved, "status": "provisional"}

    while queue and len(visited) < max_articles:
        title = queue.pop(0)
        key = slugify(title)
        if not key or key in visited:
            continue
        visited.add(key)

        html = fetcher.get(article_url(title))
        if not html:
            continue
        # Off-domain articles (karate, judo) are recorded only if an aikido article
        # already referenced them; never expanded, so adjacent arts don't bleed in.
        if not is_aikido_article(html):
            continue
        info = parse_infobox_html(html)
        url = article_url(title)
        add_person(title, url, native=info["native_name"], dan=info["dan"])

        for student in info["students"]:
            add_person(student, url)
            add_edge(student, title, url, f"Wikipedia infobox: notable students of {title}")
            if slugify(student) not in visited:
                queue.append(student)
        for teacher in info["teachers"]:
            add_person(teacher, url)
            add_edge(title, teacher, url, f"Wikipedia infobox: teacher of {title}")
            if slugify(teacher) not in visited:
                queue.append(teacher)

    return {"persons": list(persons.values()), "edges": list(edges.values()),
            "articles_visited": len(visited)}
