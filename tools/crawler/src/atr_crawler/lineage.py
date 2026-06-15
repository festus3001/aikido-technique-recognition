"""Phase E: lineage edges from tools/crawler/lineage_seed_sources.md.

That file is a hand-curated source registry for `teaches_relationship` edges:
prose sources (the Pranin "Principal Disciples" charts, Wikipedia lists and
per-teacher infoboxes) plus some confirmed inline edges in the form

    Teacher Name (org) -> Student A, Student B, Student C

This module extracts those inline arrow edges -- the immediately structured part
-- and creates a `person` stub for everyone referenced so the edges resolve. The
arrow edges come from Wikipedia "Notable students" infobox fields, which state
the link explicitly, so they are tagged `confidence: stated`. The bulleted prose
sources are returned as a registry for the live crawl to walk later (fetching and
parsing the Pranin charts and per-teacher articles is the network job that turns
the rest of the registry into edges, tagged stated where the source states the
link and inferred where it only implies it).

Edges and persons enter as `status: provisional`, subject to teacher correction.
"""

from __future__ import annotations

import re
from pathlib import Path

from .slugs import edge_id, person_id, slugify

DEFAULT_LINEAGE_PATH = Path(__file__).resolve().parents[2] / "lineage_seed_sources.md"

_PAREN = re.compile(r"\([^)]*\)")          # drop "(Yoshinkan)", "(ASU)", ...
_ARROW = re.compile(r"->|→")
_BULLET = re.compile(r"^\s*[-*]\s+")


def _wikipedia_url(name: str) -> str:
    """The teacher's Wikipedia article, where the Notable-students field lives."""
    return "https://en.wikipedia.org/wiki/" + name.strip().replace(" ", "_")


def _clean_name(raw: str) -> str:
    return _PAREN.sub("", raw).strip().strip("*").strip()


def _person_stub(name: str, source: list[str], retrieved: str) -> dict:
    return {
        "id": person_id(name),
        "name_romaji": name,
        "source": list(source),
        "retrieved": retrieved,
        "status": "provisional",
    }


def parse_lineage_sources(path: str | Path | None, retrieved: str) -> dict:
    """Parse the lineage source file.

    Returns {"edges": [...], "persons": [...], "registry": [...]} where registry
    is the list of bulleted prose sources awaiting live extraction.
    """
    path = Path(path) if path else DEFAULT_LINEAGE_PATH
    text = path.read_text(encoding="utf-8")

    edges: dict[str, dict] = {}
    persons: dict[str, dict] = {}
    registry: list[str] = []

    def add_person(name: str, source: list[str]) -> str:
        stub = _person_stub(name, source, retrieved)
        persons.setdefault(stub["id"], stub)
        return stub["id"]

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # A registered prose source, e.g. "- **Aikido Journal -- ...**"
        if stripped.startswith("- **") and not _ARROW.search(stripped):
            registry.append(_BULLET.sub("", stripped).replace("**", "").strip())
            continue

        if not _ARROW.search(stripped):
            continue

        # An inline edge line: "Teacher (org) -> Student A, Student B"
        left, right = _ARROW.split(_BULLET.sub("", stripped), maxsplit=1)
        teacher = _clean_name(left)
        if not teacher or not slugify(teacher):
            continue
        source = [_wikipedia_url(teacher)]
        teacher_id = add_person(teacher, source)
        note = "Wikipedia infobox (Notable students), via lineage_seed_sources.md"

        for chunk in right.split(","):
            student = _clean_name(chunk)
            if not student or not slugify(student) or slugify(student) == slugify(teacher):
                continue
            student_id = add_person(student, source)
            eid = edge_id(student_id, teacher_id)
            edges.setdefault(eid, {
                "id": eid,
                "student": student_id,
                "teacher": teacher_id,
                "kind": "direct-student",
                "period": None,
                "confidence": "stated",
                "notes": note,
                "source": list(source),
                "retrieved": retrieved,
                "status": "provisional",
            })

    return {"edges": list(edges.values()), "persons": list(persons.values()), "registry": registry}
