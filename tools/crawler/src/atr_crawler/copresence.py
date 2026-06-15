"""Co-presence: reconstruct relationships from overlapping tenures.

The backbone (promotion lists) only reaches back so far. For the earlier
decades the signal is who trained where, and when. Two people whose tenures at
the same dojo overlap in time were present together. Where one held a teaching
role (founder, chief-instructor, instructor) and the other a student role
(uchi-deshi, deshi, student) during the overlap, that co-presence is evidence of
a teacher->student relationship -- emitted as an `inferred` edge that a teacher
can later confirm or correct. Peer overlaps (two students, two teachers) are
recorded for the report but never asserted as lineage edges.

Every inferred edge carries its provenance: the union of the two tenures' sources
and a note naming the dojo and the overlap years.
"""

from __future__ import annotations

from itertools import combinations

from .slugs import edge_id

TEACHER_ROLES = {"founder", "chief-instructor", "instructor"}
STUDENT_ROLES = {"uchi-deshi", "deshi", "student"}

_OPEN = 9999  # sentinel end-year for an open-ended (ongoing/unknown-end) tenure


def _year(value) -> int | None:
    if value is None:
        return None
    s = str(value)
    return int(s) if s.isdigit() else None


def _overlap(a: dict, b: dict) -> tuple[int, int | None] | None:
    """Return (start, end) of the overlap in years, or None if they do not
    overlap or a start year is unknown. end is None when open-ended."""
    sa, sb = _year(a.get("start")), _year(b.get("start"))
    if sa is None or sb is None:
        return None  # cannot place an unknown-start tenure in time
    ea = _year(a.get("end")) if a.get("end") is not None else _OPEN
    eb = _year(b.get("end")) if b.get("end") is not None else _OPEN
    lo, hi = max(sa, sb), min(ea, eb)
    if lo > hi:
        return None
    return (lo, None if hi == _OPEN else hi)


def _range_label(lo: int, hi: int | None) -> str:
    return f"{lo}-{hi}" if hi is not None else f"{lo}-ongoing"


def _directional(role_a: str, role_b: str) -> str | None:
    """Return 'a_teaches_b', 'b_teaches_a', or None for a peer overlap."""
    a_t, a_s = role_a in TEACHER_ROLES, role_a in STUDENT_ROLES
    b_t, b_s = role_b in TEACHER_ROLES, role_b in STUDENT_ROLES
    if a_t and b_s:
        return "a_teaches_b"
    if b_t and a_s:
        return "b_teaches_a"
    return None


def derive_copresence(tenures: list[dict]) -> dict:
    """From tenure records, derive inferred teacher edges and a co-presence list.

    Returns {"edges": [...teaches_relationship...], "pairs": [...report rows...]}.
    Edges are aggregated by (student, teacher): if a pair overlaps at more than
    one dojo, sources and notes are combined into a single edge.
    """
    by_dojo: dict[str, list[dict]] = {}
    for t in tenures:
        by_dojo.setdefault(t["dojo"], []).append(t)

    edges: dict[str, dict] = {}
    pairs: list[dict] = []

    for dojo, group in by_dojo.items():
        for a, b in combinations(group, 2):
            if a["person"] == b["person"]:
                continue
            ov = _overlap(a, b)
            if ov is None:
                continue
            lo, hi = ov
            direction = _directional(a["role"], b["role"])
            pairs.append({
                "dojo": dojo,
                "person_a": a["person"], "role_a": a["role"],
                "person_b": b["person"], "role_b": b["role"],
                "overlap": _range_label(lo, hi),
                "directional": direction is not None,
            })
            if direction is None:
                continue

            if direction == "a_teaches_b":
                teacher, student, s_role = a, b, b["role"]
            else:
                teacher, student, s_role = b, a, a["role"]

            kind = "uchi-deshi" if s_role == "uchi-deshi" else "direct-student"
            note = f"inferred from co-presence at {dojo} ({_range_label(lo, hi)})"
            eid = edge_id(student["person"], teacher["person"])
            retrieved = max(teacher.get("retrieved", ""), student.get("retrieved", ""))
            sources = list(dict.fromkeys([*teacher.get("source", []), *student.get("source", [])]))

            if eid in edges:
                e = edges[eid]
                e["source"] = list(dict.fromkeys([*e["source"], *sources]))
                e["notes"] = f"{e['notes']}; {note}"
                e["retrieved"] = max(e["retrieved"], retrieved)
                if kind == "uchi-deshi":
                    e["kind"] = "uchi-deshi"
            else:
                edges[eid] = {
                    "id": eid,
                    "student": student["person"],
                    "teacher": teacher["person"],
                    "kind": kind,
                    "period": _range_label(lo, hi),
                    "confidence": "inferred",
                    "notes": note,
                    "source": sources,
                    "retrieved": retrieved,
                    "status": "provisional",
                }

    return {"edges": list(edges.values()), "pairs": pairs}
