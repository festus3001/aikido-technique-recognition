"""Phase F: reconcile name variants of the same person.

Across promotion lists, four federation locators, lineage sources, and seeds, the
same person shows up under different spellings -- "Y. Yamada" vs "Yoshimitsu
Yamada", "William R. Ross" vs "William Ross", a name with and without an
honorific. These get different slug ids, so they do not auto-merge.

This module finds those variants, bucketed by surname so comparison is cheap, and
sorts them into two tiers:

  high   -- same full first name + surname, differing only by a middle initial,
            an honorific, or one side abbreviating the other; or a shared
            name_native. Safe to merge.
  medium -- surname plus a first-initial match ("Y. Yamada" / "Yoshimitsu
            Yamada"). Plausible but ambiguous -- review only.

By default Phase F only writes a review queue (no silent overwrites). With
apply_merges, the high tier is merged into the fullest-named record: aliases and
sources are combined, and every reference (rank_events, tenures, edges, dojo
instructors) is re-pointed and its id rewritten.
"""

from __future__ import annotations

import re
from itertools import combinations

from .slugs import edge_id, normalize_romaji, rank_event_id, tenure_id
from .store import merge_record

# Honorifics, titles, and generational suffixes that are not part of the name.
NAME_STOP = {
    "sensei", "shihan", "shidoin", "fukushidoin", "kaicho", "doshu",
    "jr", "sr", "ii", "iii", "iv", "dr", "mr", "mrs", "ms",
}


def _tokens(name: str) -> list[str]:
    base = re.sub(r"[^a-z0-9 ]", " ", normalize_romaji(name))
    return [t for t in base.split() if t and t not in NAME_STOP]


def _initial_compat(x: str, y: str) -> bool:
    return x == y or (len(x) == 1 and y.startswith(x)) or (len(y) == 1 and x.startswith(y))


def _middles_compat(am: list[str], bm: list[str]) -> bool:
    if not am or not bm:
        return True
    if len(am) != len(bm):
        return False
    return all(_initial_compat(a, b) for a, b in zip(am, bm))


def _pair_tier(a: list[str], b: list[str]) -> str | None:
    if len(a) < 2 or len(b) < 2 or a[-1] != b[-1]:
        return None
    if not _initial_compat(a[0], b[0]):
        return None
    first_full = len(a[0]) > 1 and len(b[0]) > 1 and a[0] == b[0]
    if first_full and _middles_compat(a[1:-1], b[1:-1]):
        return "high"
    return "medium"


class _UnionFind:
    def __init__(self):
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def _score(person: dict) -> tuple:
    """Canonical preference: fuller name, then more sources, then stable id."""
    return (len(_tokens(person.get("name_romaji", ""))), len(person.get("source", [])))


def find_candidates(persons: list[dict]) -> dict:
    """Return {"high": [clusters], "medium": [clusters]}. Each cluster is
    {members, names} (high clusters also carry canonical). High clusters are
    internally consistent (every pair high-compatible) and safe to merge; a
    cluster with any conflicting pair -- e.g. plain "Andrew Demko" linking
    "Andrew L. Demko" and "Andrew P. Demko" -- is demoted to medium for review."""
    by_id = {p["id"]: p for p in persons}
    toks = {p["id"]: _tokens(p.get("name_romaji", "")) for p in persons}
    natives = {p["id"]: p.get("name_native") for p in persons}

    # Bucket by surname so we only compare plausibly-related names.
    by_surname: dict[str, list[str]] = {}
    for pid, t in toks.items():
        if len(t) >= 2:
            by_surname.setdefault(t[-1], []).append(pid)

    uf = _UnionFind()
    for ids in by_surname.values():
        for a, b in combinations(ids, 2):
            if _pair_tier(toks[a], toks[b]) is not None:  # link any plausible pair; tier checked per-cluster
                uf.union(a, b)

    # name_native exact match is also a strong link.
    by_native: dict[str, list[str]] = {}
    for pid, nat in natives.items():
        if nat:
            by_native.setdefault(nat, []).append(pid)
    for ids in by_native.values():
        for other in ids[1:]:
            uf.union(ids[0], other)

    clusters: dict[str, list[str]] = {}
    for pid in toks:
        if pid in uf.parent:
            clusters.setdefault(uf.find(pid), []).append(pid)

    def consistent(members: list[str]) -> bool:
        for a, b in combinations(members, 2):
            same_native = natives[a] and natives[a] == natives[b]
            if not same_native and _pair_tier(toks[a], toks[b]) != "high":
                return False
        return True

    high: list[dict] = []
    medium: list[dict] = []
    for members in clusters.values():
        if len(members) < 2:
            continue
        members = sorted(members)
        names = {pid: by_id[pid]["name_romaji"] for pid in members}
        if consistent(members):
            canonical = max(members, key=lambda pid: (*_score(by_id[pid]), pid))
            high.append({"canonical": canonical, "members": members, "names": names})
        else:
            medium.append({"members": members, "names": names,
                           "reason": "conflicting name variants; needs human/teacher confirmation"})
    return {"high": high, "medium": medium}


def _union(a: list, b: list) -> list:
    out, seen = [], set()
    for x in (*(a or []), *(b or [])):
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _repoint(store, old: str, new: str) -> None:
    """Re-point every reference from person `old` to `new`, rewriting ids."""
    def rekey(bucket: dict, rid: str, new_id: str, rec: dict):
        del bucket[rid]
        rec["id"] = new_id
        bucket[new_id] = merge_record(bucket[new_id], rec) if new_id in bucket else rec

    events = store.data["rank_events"]
    for rid in list(events):
        e = events[rid]
        if e["person"] == old:
            e["person"] = new
            rekey(events, rid, rank_event_id(new, e["date"], e["dan"]), e)

    tenures = store.data["tenures"]
    for tid in list(tenures):
        t = tenures[tid]
        if t["person"] == old:
            t["person"] = new
            rekey(tenures, tid, tenure_id(new, t["dojo"], t.get("start")), t)

    edges = store.data["edges"]
    for eid in list(edges):
        e = edges.get(eid)
        if e is None:
            continue
        if e["student"] == old or e["teacher"] == old:
            e["student"] = new if e["student"] == old else e["student"]
            e["teacher"] = new if e["teacher"] == old else e["teacher"]
            if e["student"] == e["teacher"]:
                del edges[eid]  # a person does not teach themselves
                continue
            rekey(edges, eid, edge_id(e["student"], e["teacher"]), e)

    for d in store.data["dojos"].values():
        if d.get("chief_instructor") == old:
            d["chief_instructor"] = new
        if d.get("instructors"):
            d["instructors"] = _union([new if x == old else x for x in d["instructors"]], [])


def apply_merges(store, high_clusters: list[dict]) -> int:
    """Merge each high-confidence cluster into its canonical record. Returns the
    number of duplicate persons absorbed."""
    persons = store.data["persons"]
    absorbed = 0
    for cluster in high_clusters:
        canon_id = cluster["canonical"]
        canon = persons.get(canon_id)
        if canon is None:
            continue
        for dup_id in cluster["members"]:
            if dup_id == canon_id or dup_id not in persons:
                continue
            dup = persons.pop(dup_id)
            aliases = set(canon.get("aliases") or []) | set(dup.get("aliases") or [])
            aliases.add(dup["name_romaji"])
            aliases.discard(canon["name_romaji"])
            canon["aliases"] = sorted(aliases)
            canon["source"] = _union(canon.get("source", []), dup.get("source", []))
            canon["retrieved"] = max(canon.get("retrieved", ""), dup.get("retrieved", ""))
            for field in ("name_native", "born", "died", "notes", "current_rank"):
                if not canon.get(field) and dup.get(field):
                    canon[field] = dup[field]
            if dup.get("deceased"):
                canon["deceased"] = True
            _repoint(store, dup_id, canon_id)
            absorbed += 1
    return absorbed
