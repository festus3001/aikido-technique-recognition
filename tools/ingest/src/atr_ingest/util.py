"""Small shared helpers: slugs and ascii folding."""

from __future__ import annotations

import re
import unicodedata

_NON_SLUG = re.compile(r"[^a-z0-9]+")


def fold(text: str) -> str:
    """Drop diacritics (macrons especially: Kokyū -> Kokyu) and lowercase."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return stripped.lower().strip()


def slugify(text: str) -> str:
    return _NON_SLUG.sub("-", fold(text)).strip("-")
