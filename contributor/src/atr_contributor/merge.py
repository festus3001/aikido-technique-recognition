"""Project teacher Refinements onto the provisional corpus.

Resolves the technique-scope Refinements (name / parse.slots / keyframe.sequence / verdict /
note) onto each technique and writes techniques_reviewed.json -- the teacher-authorized view
that D3 motifs / F1 dataset / F2,F4 model train and evaluate against. The provisional
techniques.json is never modified; techniques_reviewed.json is a regenerable build artifact.

  atr-review-merge
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from schema.refinement import RefinementStore, matching, resolve

from .store import REFINEMENTS, TAXO, TECHNIQUES, _load, _write_atomic

REVIEWED = TAXO / "techniques_reviewed.json"


def project() -> tuple[list, dict]:
    techniques = _load(TECHNIQUES, [])
    refs = RefinementStore(path=REFINEMENTS)
    out, counts = [], defaultdict(int)
    for t in techniques:
        unit = {"technique": t["id"]}
        vrefs = matching("verdict", unit, refs)
        verdict = vrefs[-1].payload.get("verdict") if vrefs else None
        rec = dict(t)
        if verdict in ("confirmed", "corrected"):
            name = resolve("name", unit, refs, base=None)
            slots = resolve("parse.slots", unit, refs, base=None)
            kf = resolve("keyframe.sequence", unit, refs, base=None)
            note = resolve("note", unit, refs, base=None)
            if name:
                rec["name_romaji"] = name.get("romaji") or t.get("name_romaji")
                rec["name_native"] = name.get("native") or t.get("name_native")
            if slots:
                rec["slots"] = {**t.get("slots", {}),
                                **{k: v for k, v in slots.items() if v not in (None, [])}}
            if kf and kf.get("sequence"):
                rec["keyframes_reviewed"] = kf["sequence"]
            rec["status"] = "reviewed"
            p = vrefs[-1].provenance
            rec["review"] = {"verdict": verdict, "note": (note.get("text") if note else None),
                             "reviewed_by": p.author, "date": p.date}
            counts[verdict] += 1
        elif verdict == "rejected":
            rec["status"] = "rejected"
            p = vrefs[-1].provenance
            rec["review"] = {"verdict": "rejected", "reviewed_by": p.author, "date": p.date}
            counts["rejected"] += 1
        else:
            counts["skip" if verdict else "unreviewed"] += 1
        out.append(rec)
    return out, dict(counts)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="atr-review-merge", description="Project reviews onto the corpus")
    p.add_argument("--out", default=str(REVIEWED))
    args = p.parse_args(argv)
    out, counts = project()
    _write_atomic(Path(args.out), out)
    print(f"Wrote {len(out)} techniques -> {args.out}")
    for k in ("confirmed", "corrected", "rejected", "skip", "unreviewed"):
        if counts.get(k):
            print(f"  {k:>10}: {counts[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
