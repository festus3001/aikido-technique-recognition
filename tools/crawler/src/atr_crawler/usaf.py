"""Phase B parser: USAF Kagamibiraki annual promotion lists.

Source: usaikifed.com/post/<year>-kagamibiraki-promotions. The post body is
server-side rendered plain text -- rank headings ("5th Dan:", "Shihan") followed
by "Name - Dojo" lines:

    5th Dan:
    Virginia Becart - Florida Aikikai
    John Donnelly - Boston Aikikai
    ...

Each dan line becomes a `rank_event` (the backbone), creating the `person` and
`dojo` it implies. USAF lists 5th dan and above (New Year recommendations);
lower grades are dojo-level and not published here. A "Shihan" section confers a
title, not a dan, so those entries update the person's notes rather than emitting
a rank_event (which requires a dan).

Source text is preserved verbatim, including its own typos (e.g. "Aikikai if
Philadelphia") -- the crawler records what the source says; corrections are a
reconcile/teacher step, not a parse-time guess.
"""

from __future__ import annotations

import re

from .slugs import dojo_id, person_id, rank_event_id, slugify

USAF_URL = "https://www.usaikifed.com/post/{year}-kagamibiraki-promotions"

_ROMAJI_DAN = {
    "shodan": 1, "nidan": 2, "sandan": 3, "yondan": 4, "yodan": 4, "godan": 5,
    "rokudan": 6, "nanadan": 7, "shichidan": 7, "hachidan": 8, "kyudan": 9,
    "kudan": 9, "judan": 10,
}
_SEP = re.compile(r"\s+[-–—]\s+")  # " - ", en dash, em dash
_DAN_HEAD = re.compile(r"^(\d{1,2})(?:st|nd|rd|th)\s+dan\b", re.I)
_ROMAJI_HEAD = re.compile(r"^(" + "|".join(_ROMAJI_DAN) + r")\b", re.I)
_SHIHAN_HEAD = re.compile(r"^shihan\b", re.I)


def _heading(line: str):
    """Return ('dan', n) | ('shihan', None) | None for a section heading line."""
    if _SEP.search(line) or len(line) > 24:
        return None  # entries carry a separator; headings are short and don't
    if _SHIHAN_HEAD.match(line):
        return ("shihan", None)
    m = _DAN_HEAD.match(line)
    if m:
        return ("dan", int(m.group(1)))
    m = _ROMAJI_HEAD.match(line)
    if m:
        return ("dan", _ROMAJI_DAN[m.group(1).lower()])
    return None


def _split_entry(line: str):
    """Split 'Name - Dojo' into (name, dojo), or None if it is not an entry."""
    parts = _SEP.split(line, maxsplit=1)
    if len(parts) != 2:
        return None
    name, dojo = parts[0].strip(), parts[1].strip()
    if not name or not dojo or len(name) > 40 or len(dojo) > 60:
        return None
    if not name[0].isupper() or not slugify(name) or not slugify(dojo):
        return None
    tokens = name.split()
    if len(tokens) > 6:
        return None
    # A name is capitalized tokens (with at most one lowercase particle like "de");
    # this rejects prose lines such as "Stay tuned for more news".
    if sum(1 for t in tokens if t[:1].islower()) >= 2:
        return None
    return name, dojo


def html_to_text(html: str) -> str:
    """Render HTML to newline-separated text, dropping script/style noise."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text("\n")


def parse_kagamibiraki(text: str, year: int, retrieved: str, source_url: str | None = None) -> dict:
    """Parse one year's promotion text. Returns persons, dojos, rank_events, and
    shihan_titles (person updates for the Shihan section)."""
    source = [source_url or USAF_URL.format(year=year)]
    date = f"{year}-01-01"

    persons: dict[str, dict] = {}
    dojos: dict[str, dict] = {}
    rank_events: dict[str, dict] = {}
    shihan: list[str] = []

    mode = None  # ("dan", n) | ("shihan", None) | None
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    def add_person(name: str, notes: str | None = None) -> str:
        pid = person_id(name)
        rec = persons.get(pid) or {
            "id": pid, "name_romaji": name, "source": list(source),
            "retrieved": retrieved, "status": "provisional",
        }
        if notes:
            rec["notes"] = notes
        persons[pid] = rec
        return pid

    def add_dojo(name: str) -> str:
        did = dojo_id(name)
        dojos.setdefault(did, {
            "id": did, "name": name, "org": ["org:usaf"],
            "source": list(source), "retrieved": retrieved, "status": "provisional",
        })
        return did

    for line in lines:
        head = _heading(line)
        if head is not None:
            mode = head
            continue
        if mode is None:
            continue
        entry = _split_entry(line)
        if entry is None:
            mode = None  # first non-entry line ends the section
            continue
        name, dojo_name = entry
        if mode[0] == "shihan":
            add_person(name, notes=f"Shihan title conferred {year} (USAF Kagamibiraki).")
            shihan.append(person_id(name))
            continue
        dan = mode[1]
        pid = add_person(name)
        did = add_dojo(dojo_name)
        rid = rank_event_id(pid, date, dan)
        rank_events[rid] = {
            "id": rid, "person": pid, "dan": dan, "title": None, "date": date,
            "conferred_by": "org:aikikai-hombu", "via_org": "org:usaf", "dojo": did,
            "source": list(source), "retrieved": retrieved,
        }

    return {
        "persons": list(persons.values()),
        "dojos": list(dojos.values()),
        "rank_events": list(rank_events.values()),
        "shihan_titles": shihan,
    }
