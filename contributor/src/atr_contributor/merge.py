"""Project the teacher's reviews onto the provisional corpus.

Reads techniques.json + reviews.json and writes techniques_reviewed.json: each technique
carries the teacher-approved name/slots where a review exists, the corrected keyframe
sequence if the teacher edited it, and a `review` block (who/when/verdict + the deep-layer
note). The provisional techniques.json is never modified -- this is the downstream-consumable,
teacher-authorized view (what D3 motifs / F1 dataset / F2 parse model train and evaluate
against).

  atr-review-merge            # write data/taxonomy/techniques_reviewed.json + print a summary
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from .store import REVIEWS, TAXO, TECHNIQUES, _load, _write_atomic

REVIEWED = TAXO / "techniques_reviewed.json"


def project() -> tuple[list, dict]:
    techniques = _load(TECHNIQUES, [])
    reviews = _load(REVIEWS, [])
    best: dict[str, dict] = {}
    for r in reviews:
        cur = best.get(r["technique"])
        if cur is None or r.get("date", "") >= cur.get("date", ""):
            best[r["technique"]] = r

    out, counts = [], defaultdict(int)
    for t in techniques:
        r = best.get(t["id"])
        rec = dict(t)
        if r and r["verdict"] in ("confirmed", "corrected"):
            rec["name_romaji"] = r.get("name_romaji") or t.get("name_romaji")
            rec["name_native"] = r.get("name_native") or t.get("name_native")
            rec["slots"] = {**t.get("slots", {}),
                            **{k: v for k, v in r.get("slots", {}).items() if v not in (None, [])}}
            if r.get("keyframes"):
                rec["keyframes_reviewed"] = r["keyframes"]
            rec["status"] = "reviewed"
            rec["review"] = {
                "verdict": r["verdict"], "note": r.get("note"),
                "reviewed_by": r["reviewed_by"], "reviewed_by_name": r.get("reviewed_by_name"),
                "date": r["date"],
            }
            counts[r["verdict"]] += 1
        elif r and r["verdict"] == "rejected":
            rec["status"] = "rejected"
            rec["review"] = {"verdict": "rejected", "reviewed_by": r["reviewed_by"], "date": r["date"]}
            counts["rejected"] += 1
        else:
            counts["unreviewed" if not r else "skip"] += 1
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
