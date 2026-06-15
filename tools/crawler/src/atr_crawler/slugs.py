"""Stable slug ids and name normalization.

Slugs are the merge key for the whole map: the same person, dojo, or org must
always produce the same id so re-crawls update rather than duplicate. Romaji
names are normalized by stripping diacritics (macrons especially: Saito ->
Saito, Tohei stays Tohei), lowercasing, and hyphenating.
"""

from __future__ import annotations

import re
import unicodedata

_NON_SLUG = re.compile(r"[^a-z0-9]+")


def normalize_romaji(name: str) -> str:
    """Fold a romaji name to ascii, dropping macrons and other diacritics.

    "Koichi Tohei" -> "koichi tohei"; "Morihiro Saito" with a macron on the
    first o -> "morihiro saito". Combining marks are removed after NFKD
    decomposition so o-macron collapses to o.
    """
    decomposed = unicodedata.normalize("NFKD", name)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return stripped.lower().strip()


def slugify(text: str) -> str:
    """Lowercase ascii slug body: spaces and punctuation to single hyphens."""
    folded = normalize_romaji(text)
    slug = _NON_SLUG.sub("-", folded).strip("-")
    return slug


def entity_id(kind: str, name: str) -> str:
    """Build a namespaced entity id, e.g. person_id('Akira Tohei')."""
    body = slugify(name)
    if not body:
        raise ValueError(f"cannot build a {kind} id from empty name: {name!r}")
    return f"{kind}:{body}"


def person_id(name: str) -> str:
    return entity_id("person", name)


def org_id(name_or_abbrev: str) -> str:
    return entity_id("org", name_or_abbrev)


def dojo_id(name: str) -> str:
    return entity_id("dojo", name)


def rank_event_id(person: str, date: str, dan: int) -> str:
    """rank:<person-slug>+<date>+<dan>. person is a full person id or a name."""
    p = person.split(":", 1)[-1] if person.startswith("person:") else slugify(person)
    return f"rank:{p}+{date}+{dan}"


def tenure_id(person: str, dojo: str, start: str | None) -> str:
    """tenure:<person-slug>+<dojo-slug>+<start-or-unknown>."""
    p = person.split(":", 1)[-1] if person.startswith("person:") else slugify(person)
    d = dojo.split(":", 1)[-1] if dojo.startswith("dojo:") else slugify(dojo)
    return f"tenure:{p}+{d}+{start or 'unknown'}"


def edge_id(student: str, teacher: str) -> str:
    """edge:<student-slug>+<teacher-slug>."""
    s = student.split(":", 1)[-1] if student.startswith("person:") else slugify(student)
    t = teacher.split(":", 1)[-1] if teacher.startswith("person:") else slugify(teacher)
    return f"edge:{s}+{t}"
