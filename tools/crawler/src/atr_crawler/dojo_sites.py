"""Phase D: individual dojo sites (the long tail).

Unlike the federation locators (one structure each), dojo websites are all
different, so there is no single parser. This phase is deliberately
high-precision and low-yield: it follows a dojo site's own instructor/about
links and extracts a name only when it sits next to an explicit signal -- a
"Chief Instructor" label, "Sensei", or a dan rank. Anything weaker is skipped
rather than guessed. Extracted instructors are provisional and a starting point
for teacher confirmation, not an authority.

Because this touches many external hosts, it is opt-in (--phase-d) and bounded
(--max-dojo-sites), and it follows the site's own navigation (at most a few
pages per dojo) rather than probing guessed paths.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from .slugs import person_id, slugify

_NAME = r"[A-Z][a-zA-Z'’.\-]+(?:\s+[A-Z][a-zA-Z'’.\-]+){1,2}"
_SENSEI_AFTER = re.compile(rf"\b({_NAME})\s+Sensei\b")
_SENSEI_BEFORE = re.compile(rf"\bSensei\s+({_NAME})\b")
_RANK = re.compile(rf"\b({_NAME}),?\s+\d(?:st|nd|rd|th)\s+[Dd]an\b")
_CHIEF = re.compile(rf"(?:Chief|Head|Founding|Dojo[- ]?cho)\s+Instructor[:,\s]+({_NAME})\b", re.I)

# A token that appears in any of these means it is not a personal name.
_NOT_NAME = {
    "aikido", "aikikai", "dojo", "sensei", "shihan", "shidoin", "fukushidoin",
    "federation", "association", "alliance", "ki", "society", "school", "schools",
    "martial", "arts", "class", "classes", "children", "youth", "adult", "home",
    "about", "contact", "schedule", "privacy", "copyright", "instructor", "instructors",
    "dan", "kyu", "cho", "project", "legacy", "center", "centre", "club", "hombu",
    "welcome", "rights", "reserved", "the", "and", "our", "main", "head", "chief",
}

_LINK_HINT = re.compile(r"instructor|sensei|teacher|about|staff|faculty|dojo[- ]?cho", re.I)

_TITLE = re.compile(r"[A-Z][a-z]+")  # a Title-case word (not ALL-CAPS, not an initial)


def _looks_like_name(name: str) -> bool:
    tokens = [t.strip(".").strip() for t in name.split()]
    tokens = [t for t in tokens if t]
    if not (2 <= len(tokens) <= 3):
        return False
    title_count = 0
    for t in tokens:
        if _TITLE.fullmatch(t):                 # real word, e.g. "Robert"
            if slugify(t) in _NOT_NAME:
                return False
            title_count += 1
        elif re.fullmatch(r"[A-Z]", t):         # a middle initial, e.g. "A"
            continue
        else:                                   # ALL-CAPS, mixed case, digits, etc.
            return False
    return title_count >= 2


def extract_instructors(html: str) -> list[dict]:
    """Return [{name, role}] where role is 'chief' or 'instructor'. High-precision:
    a name is taken only when it sits next to an explicit signal within the same
    text block (per-block, not whole-page, to avoid cross-element false matches)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    found: dict[str, str] = {}  # name -> role (chief wins over instructor)
    for block in soup.get_text("\n").split("\n"):
        block = block.strip()
        if not block or len(block) > 160:
            continue
        for name in _CHIEF.findall(block):
            if _looks_like_name(name):
                found[name] = "chief"
        for pattern in (_SENSEI_AFTER, _SENSEI_BEFORE, _RANK):
            for name in pattern.findall(block):
                if _looks_like_name(name):
                    found.setdefault(name, "instructor")
    return [{"name": n, "role": r} for n, r in found.items()]


def find_instructor_links(html: str, base_url: str) -> list[str]:
    """Same-host links whose text or href hints at an instructor/about page."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    host = urlparse(base_url).netloc
    out: list[str] = []
    seen: set = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not _LINK_HINT.search(href) and not _LINK_HINT.search(a.get_text(" ", strip=True)):
            continue
        full = urljoin(base_url, href)
        if urlparse(full).netloc != host:
            continue
        full = full.split("#")[0]
        if full not in seen and full.rstrip("/") != base_url.rstrip("/"):
            seen.add(full)
            out.append(full)
    return out[:2]  # at most two extra pages per dojo


def crawl_dojo_sites(fetcher, dojos: list[dict], retrieved: str, limit: int | None = None) -> dict:
    """Crawl dojo websites for instructors. Returns {persons, dojo_updates} where
    dojo_updates maps dojo_id -> {"instructors": [...], "chief": id|None, "source": url}."""
    persons: dict[str, dict] = {}
    dojo_updates: dict[str, dict] = {}
    targets = [d for d in dojos if d.get("website")]
    if limit is not None:
        targets = targets[:limit]

    for dojo in targets:
        url = dojo["website"]
        home = fetcher.get(url)
        if not home:
            continue
        pages = [(url, home)]
        for link in find_instructor_links(home, url):
            page = fetcher.get(link)
            if page:
                pages.append((link, page))

        names: dict[str, str] = {}
        src_page = None
        for page_url, html in pages:
            for rec in extract_instructors(html):
                if rec["name"] not in names or rec["role"] == "chief":
                    names[rec["name"]] = rec["role"]
                    src_page = src_page or page_url
        if not names:
            continue

        instr_ids: list[str] = []
        chief_id = None
        for name, role in names.items():
            pid = person_id(name)
            persons.setdefault(pid, {
                "id": pid, "name_romaji": name, "source": [src_page],
                "retrieved": retrieved, "status": "provisional",
                "notes": "instructor extracted from dojo website (unverified).",
            })
            instr_ids.append(pid)
            if role == "chief" and chief_id is None:
                chief_id = pid
        dojo_updates[dojo["id"]] = {"instructors": instr_ids, "chief": chief_id, "source": src_page}

    return {"persons": list(persons.values()), "dojo_updates": dojo_updates}
