"""Refinement -- the project's scoped, attributed interpretation-correction primitive.

A Refinement is one correction that refines an interpretation at a scope (process .. technique),
authored by someone (CARE provenance, schema/contribution.py). It is the single, reusable shape
for every correction in the project: ingestion tuning (lexicon, section map, page region/caption
fixes) AND teacher review (a technique's name, slots, keyframe sequence, verdict, note) are the
same object at different scopes/targets.

Resolution is a cascade. Code defaults are the base layer; stored Refinements layer on top,
ordered broad -> narrow (then by date), folded per each target's merge semantic. So progressive
refinement is literal: corrections accumulate as attributed Refinements and the resolver always
yields the current effective interpretation. New consumers (AML motifs, video-keyframe matching,
parse-model post-edits) register a target; the primitive does not change.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .contribution import Provenance

REPO_ROOT = Path(__file__).resolve().parents[1]
REFINEMENTS_PATH = REPO_ROOT / "data" / "refinements.json"

# scope levels, broadest -> narrowest
LEVELS = ["process", "corpus", "book", "section", "page", "sequence", "technique"]
_RANK = {lvl: i for i, lvl in enumerate(LEVELS)}

# target -> the scope levels it is valid at and how the resolver folds matching Refinements:
#   override -- narrowest scope, then latest, wins (single value over the base)
#   additive -- all matching contribute (folded onto the base by a consumer-supplied combiner)
#   compose  -- matching payloads are ordered ops applied in sequence onto the base
TARGETS: dict[str, dict] = {
    "lexicon.entry":     {"levels": ["process", "corpus", "book"], "merge": "additive"},
    "book.offset":       {"levels": ["book"], "merge": "override"},
    "section":           {"levels": ["book"], "merge": "override"},   # selector carries a page range
    "region.ops":        {"levels": ["page", "sequence"], "merge": "compose"},
    "caption":           {"levels": ["page", "sequence"], "merge": "override"},
    "link.sequence":     {"levels": ["page"], "merge": "override"},
    "name":              {"levels": ["technique"], "merge": "override"},
    "parse.slots":       {"levels": ["technique"], "merge": "override"},
    "keyframe.sequence": {"levels": ["technique"], "merge": "override"},
    "verdict":           {"levels": ["technique"], "merge": "override"},
    "note":              {"levels": ["technique"], "merge": "override"},
}


@dataclass
class Scope:
    level: str
    selector: dict = field(default_factory=dict)   # {} | {book} | {book,pages:[a,b]} | {book,page[,seq]} | {technique}

    def to_dict(self) -> dict:
        return {"level": self.level, "selector": self.selector}

    @classmethod
    def from_dict(cls, d: dict) -> "Scope":
        return cls(level=d["level"], selector=d.get("selector", {}))


@dataclass
class Refinement:
    id: str
    scope: Scope
    target: str
    payload: dict
    provenance: Provenance
    status: str = "provisional"            # provisional | confirmed | retired

    def to_dict(self) -> dict:
        return {"id": self.id, "scope": self.scope.to_dict(), "target": self.target,
                "payload": self.payload, "provenance": self.provenance.to_dict(),
                "status": self.status}

    @classmethod
    def from_dict(cls, d: dict) -> "Refinement":
        return cls(id=d["id"], scope=Scope.from_dict(d["scope"]), target=d["target"],
                   payload=d.get("payload", {}), provenance=Provenance.from_dict(d["provenance"]),
                   status=d.get("status", "provisional"))


def _slug(s: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def make_id(scope: Scope, target: str, payload: dict | None = None,
            author: str | None = None) -> str:
    """Stable id so re-editing the same scope+target by the same author upserts, while a
    different author's correction coexists (per-teacher attribution). Additive targets also
    key on the payload term (each vocabulary entry is its own record)."""
    s = scope.selector
    parts = [target]
    if "book" in s:
        parts.append(_slug(s["book"]))
    if "pages" in s:
        parts.append(f"p{s['pages'][0]}-{s['pages'][1]}")
    if "page" in s:
        parts.append(f"p{s['page']}")
    if "seq" in s:
        parts.append(f"s{s['seq']}")
    if "technique" in s:
        parts.append(_slug(s["technique"]))
    if TARGETS.get(target, {}).get("merge") == "additive" and payload:
        key = payload.get("canonical") or payload.get("slot") or payload.get("term") or ""
        parts.append(_slug(f"{payload.get('slot','')}-{key}"))
    if author:
        parts.append(_slug(author))
    return "ref:" + ":".join(parts)


def _matches(scope: Scope, unit: dict) -> bool:
    """A scope's selector is consistent with the interpretation unit. An empty selector
    (process) matches anything; a page range matches by containment."""
    s = scope.selector
    if "book" in s and unit.get("book") != s["book"]:
        return False
    if "technique" in s and unit.get("technique") != s["technique"]:
        return False
    if "pages" in s:
        p = unit.get("page")
        if p is None or not (s["pages"][0] <= p <= s["pages"][1]):
            return False
    if "page" in s and unit.get("page") != s["page"]:
        return False
    if "seq" in s and unit.get("seq") != s["seq"]:
        return False
    return True


class RefinementStore:
    def __init__(self, path: str | Path | None = REFINEMENTS_PATH,
                 extra: list[Refinement] | None = None):
        self.path = Path(path) if path else None
        self.items: list[Refinement] = []
        self._by_target: dict[str, list[Refinement]] = {}
        if self.path and self.path.exists():
            for d in json.loads(self.path.read_text(encoding="utf-8")):
                self.items.append(Refinement.from_dict(d))
        for r in extra or []:                 # in-flight (unsaved) refinements, e.g. live preview
            self.items.append(r)
        self._reindex()

    def _reindex(self) -> None:
        self._by_target = {}
        for r in self.items:
            self._by_target.setdefault(r.target, []).append(r)

    def by_target(self, target: str) -> list[Refinement]:
        return self._by_target.get(target, [])

    def upsert(self, ref: Refinement) -> Refinement:
        self.items = [r for r in self.items if r.id != ref.id]
        self.items.append(ref)
        self._reindex()
        return ref

    def remove(self, ref_id: str) -> None:
        self.items = [r for r in self.items if r.id != ref_id]
        self._reindex()

    def get(self, ref_id: str) -> Refinement | None:
        return next((r for r in self.items if r.id == ref_id), None)

    def add(self, level: str, target: str, payload: dict, provenance: Provenance,
            selector: dict | None = None, status: str = "provisional") -> Refinement:
        scope = Scope(level=level, selector=selector or {})
        ref = Refinement(id=make_id(scope, target, payload, author=provenance.author),
                         scope=scope, target=target, payload=payload,
                         provenance=provenance, status=status)
        return self.upsert(ref)

    def save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump([r.to_dict() for r in self.items], fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    # -- query helpers for the review tool -----------------------------------
    def query(self, target: str | None = None, unit: dict | None = None) -> list[Refinement]:
        out = [r for r in self.items if (target is None or r.target == target)
               and (unit is None or _matches(r.scope, unit))]
        return sorted(out, key=lambda r: (_RANK.get(r.scope.level, 99), r.provenance.date))


def matching(target: str, unit: dict, store: RefinementStore) -> list[Refinement]:
    """Active Refinements for a target whose scope matches the unit, broad -> narrow then by date."""
    refs = [r for r in store.by_target(target)
            if r.status != "retired" and _matches(r.scope, unit)]
    refs.sort(key=lambda r: (_RANK.get(r.scope.level, 99), r.provenance.date))
    return refs


def resolve(target: str, unit: dict, store: RefinementStore, base: Any = None,
            *, fold: Callable[[Any, list[dict]], Any] | None = None) -> Any:
    """The effective interpretation for `target` at `unit`, folding matching Refinements onto
    `base` (the code-seed default) per the target's merge semantic.

    - override: the narrowest/latest matching payload, else base.
    - additive: fold(base, [payloads]) -- the consumer supplies the combiner (e.g. lexicon insert).
    - compose:  fold(base, [payloads]) if given, else the ordered op payloads (caller applies).
    """
    refs = matching(target, unit, store)
    sem = TARGETS.get(target, {}).get("merge", "override")
    payloads = [r.payload for r in refs]
    if sem == "override":
        return payloads[-1] if payloads else base
    if fold is not None:
        return fold(base, payloads)
    if sem == "additive":
        return _default_additive(base, payloads)
    return payloads  # compose: ordered ops for the caller to apply onto base


def _default_additive(base: Any, payloads: list[dict]) -> Any:
    """Shallow union used when no consumer combiner is supplied: base dict updated by each
    payload (lists extended, dicts merged one level)."""
    out = dict(base or {})
    for p in payloads:
        for k, v in p.items():
            if isinstance(v, list) and isinstance(out.get(k), list):
                out[k] = out[k] + [x for x in v if x not in out[k]]
            elif isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k] = {**out[k], **v}
            else:
                out[k] = v
    return out
