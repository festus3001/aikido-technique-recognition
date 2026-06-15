"""Idempotent JSON store: merge by stable id, never silently duplicate.

One file per collection under data/map/. Records are merged by id with
field-aware rules so a re-crawl updates in place:

  - source:      union (dedupe, order-preserving) -- accumulate provenance
  - retrieved:   keep the latest date
  - confidence:  keep the strongest (a stated edge is never demoted to
                 inferred; a contested flag sticks for review)
  - list fields: union (aliases, instructors, org affiliations)
  - dict fields: recursive non-null override (current_rank, location)
  - scalars:     incoming non-null overrides; null never erases an existing value

Records are written sorted by id so the on-disk diff is stable across runs
regardless of the order the crawl encountered them.
"""

from __future__ import annotations

import json
from pathlib import Path

# Logical collection -> (filename, schema $def name).
COLLECTIONS: dict[str, tuple[str, str]] = {
    "persons": ("persons.json", "person"),
    "organizations": ("organizations.json", "organization"),
    "dojos": ("dojos.json", "dojo"),
    "rank_events": ("rank_events.json", "rank_event"),
    "tenures": ("tenures.json", "tenure"),
    "edges": ("edges.json", "teaches_relationship"),
}

# Higher wins. Used to merge the `confidence` field without demotion.
_CONFIDENCE_RANK = {"inferred": 0, "stated": 1, "contested": 2}


def _union(existing: list, incoming: list) -> list:
    """Order-preserving union of two lists of hashable items."""
    out: list = []
    seen: set = set()
    for item in (*(existing or []), *(incoming or [])):
        key = item if isinstance(item, (str, int, float, bool)) else json.dumps(item, sort_keys=True)
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def merge_record(existing: dict, incoming: dict) -> dict:
    """Merge incoming into existing per the field rules above."""
    result = dict(existing)
    for key, value in incoming.items():
        if key == "source":
            result[key] = _union(existing.get("source", []), value or [])
        elif key == "retrieved":
            result[key] = max(existing.get("retrieved", ""), value or "")
        elif key == "confidence" and existing.get("confidence") is not None:
            cur, new = existing["confidence"], value
            result[key] = cur if _CONFIDENCE_RANK.get(new, -1) <= _CONFIDENCE_RANK.get(cur, -1) else new
        elif isinstance(value, list):
            result[key] = _union(existing.get(key, []), value)
        elif isinstance(value, dict) and isinstance(existing.get(key), dict):
            result[key] = merge_record(existing[key], value)
        else:
            if value is not None or key not in result:
                result[key] = value
    return result


class JsonStore:
    """In-memory map of collections, persisted as data/map/<collection>.json."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.data: dict[str, dict[str, dict]] = {name: {} for name in COLLECTIONS}

    def load(self) -> "JsonStore":
        for name, (filename, _def) in COLLECTIONS.items():
            path = self.root / filename
            if path.exists():
                records = json.loads(path.read_text(encoding="utf-8"))
                self.data[name] = {rec["id"]: rec for rec in records}
        return self

    def upsert(self, collection: str, record: dict) -> dict:
        """Insert or merge a record by id. Returns the stored record."""
        if collection not in self.data:
            raise KeyError(f"unknown collection: {collection}")
        rec_id = record["id"]
        bucket = self.data[collection]
        bucket[rec_id] = merge_record(bucket[rec_id], record) if rec_id in bucket else record
        return bucket[rec_id]

    def all(self, collection: str) -> list[dict]:
        return sorted(self.data[collection].values(), key=lambda r: r["id"])

    def count(self, collection: str) -> int:
        return len(self.data[collection])

    def save(self) -> list[Path]:
        """Write every collection sorted by id. Returns the paths written."""
        self.root.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        for name, (filename, _def) in COLLECTIONS.items():
            path = self.root / filename
            records = self.all(name)
            path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            written.append(path)
        return written
