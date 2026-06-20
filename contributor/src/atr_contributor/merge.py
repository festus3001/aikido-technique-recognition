"""Project the teacher's ratifications onto the provisional corpus.

Reads techniques.json + ratifications.json and writes techniques_ratified.json: each
technique carries the teacher-approved name/slots where a ratification exists, with a
`ratification` block recording who/when/verdict and the deep-layer note. The provisional
techniques.json is never modified -- this is the downstream-consumable, teacher-authorized
view (what D3 motifs / F1 dataset / F2 parse model should train and evaluate against).

  atr-ratify-merge            # write data/taxonomy/techniques_ratified.json + print a summary
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict

from .store import RATIFICATIONS, TAXO, TECHNIQUES, _load, _write_atomic

RATIFIED = TAXO / "techniques_ratified.json"


def project() -> tuple[list, dict]:
    techniques = _load(TECHNIQUES, [])
    rats = _load(RATIFICATIONS, [])
    # latest ratification per technique (by date, then file order)
    best: dict[str, dict] = {}
    for r in rats:
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
            rec["slots"] = {**t.get("slots", {}), **{k: v for k, v in r.get("slots", {}).items() if v not in (None, [])}}
            rec["status"] = "ratified"
            rec["ratification"] = {
                "verdict": r["verdict"], "note": r.get("note"),
                "ratified_by": r["ratified_by"], "ratified_by_name": r.get("ratified_by_name"),
                "date": r["date"],
            }
            counts[r["verdict"]] += 1
        elif r and r["verdict"] == "rejected":
            rec["status"] = "rejected"
            rec["ratification"] = {"verdict": "rejected", "ratified_by": r["ratified_by"], "date": r["date"]}
            counts["rejected"] += 1
        else:
            counts["unreviewed" if not r else "skip"] += 1
        out.append(rec)
    return out, dict(counts)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="atr-ratify-merge", description="Project ratifications onto the corpus")
    p.add_argument("--out", default=str(RATIFIED))
    args = p.parse_args(argv)
    out, counts = project()
    _write_atomic(type(TECHNIQUES)(args.out), out)
    total = len(out)
    print(f"Wrote {total} techniques -> {args.out}")
    for k in ("confirmed", "corrected", "rejected", "skip", "unreviewed"):
        if counts.get(k):
            print(f"  {k:>10}: {counts[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
