"""Coverage report: what the map currently holds and where it is thin.

Writes data/map/coverage_report.md (counts per entity, promotion-year span,
dojos with vs. without instructor data, co-presence summary, validation and
reconcile flags) and data/map/review.json (records needing human attention).
"""

from __future__ import annotations

import json
from pathlib import Path


def _promotion_year_span(rank_events: list[dict]) -> str:
    years = sorted({(e.get("date") or "")[:4] for e in rank_events if e.get("date")})
    years = [y for y in years if y]
    return f"{years[0]}-{years[-1]} ({len(years)} distinct years)" if years else "none captured"


def _dojo_instructor_coverage(dojos: list[dict]) -> tuple[int, int]:
    have = sum(1 for d in dojos if d.get("chief_instructor") or d.get("instructors"))
    return have, len(dojos) - have


def write_report(root: str | Path, store, copresence: dict, lineage_registry: list[str],
                 problems: dict[str, list[str]], reconcile: dict | None = None) -> dict[str, Path]:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)

    dojos = store.all("dojos")
    have_inst, missing_inst = _dojo_instructor_coverage(dojos)
    anchors = [d for d in dojos if d.get("anchor")]
    pairs = copresence.get("pairs", [])
    directional = [p for p in pairs if p["directional"]]

    lines: list[str] = []
    lines.append("# ATR data map -- coverage report\n")
    lines.append("Provisional and subject to teacher correction. See "
                 "docs/atr_13_datamap_crawl.md.\n")

    lines.append("## Entity counts\n")
    lines.append("| collection | records |")
    lines.append("|---|---|")
    for name in ("persons", "organizations", "dojos", "rank_events", "tenures", "edges"):
        lines.append(f"| {name} | {store.count(name)} |")
    lines.append("")

    lines.append("## Promotion-list backbone\n")
    lines.append(f"- Years captured: {_promotion_year_span(store.all('rank_events'))}")
    lines.append(f"- rank_event records: {store.count('rank_events')}\n")

    lines.append("## Dojos\n")
    lines.append(f"- Total: {len(dojos)} ({len(anchors)} anchor)")
    lines.append(f"- With instructor data: {have_inst}")
    lines.append(f"- Without instructor data: {missing_inst}\n")

    lines.append("## Co-presence (pre-promotion-list reconstruction)\n")
    lines.append(f"- Tenure records: {store.count('tenures')}")
    lines.append(f"- Overlapping pairs found: {len(pairs)}")
    lines.append(f"- Directional (teacher/student) overlaps -> inferred edges: {len(directional)}")
    peer = len(pairs) - len(directional)
    lines.append(f"- Peer overlaps (recorded, not asserted as edges): {peer}\n")
    if pairs:
        lines.append("| dojo | a (role) | b (role) | overlap | directional |")
        lines.append("|---|---|---|---|---|")
        for p in sorted(pairs, key=lambda x: (x["dojo"], x["overlap"])):
            lines.append(f"| {p['dojo']} | {p['person_a']} ({p['role_a']}) | "
                         f"{p['person_b']} ({p['role_b']}) | {p['overlap']} | "
                         f"{'yes' if p['directional'] else 'no'} |")
        lines.append("")

    lines.append("## Lineage sources pending live extraction (Phase E)\n")
    if lineage_registry:
        for src in lineage_registry:
            lines.append(f"- {src}")
    else:
        lines.append("- none registered")
    lines.append("")

    reconcile = reconcile or {"high": [], "medium": []}
    lines.append("## Reconcile (name-variant duplicates)\n")
    lines.append(f"- High-confidence clusters: {len(reconcile['high'])}")
    lines.append(f"- Medium pairs (review only): {len(reconcile['medium'])}\n")
    for c in reconcile["high"][:25]:
        members = ", ".join(f"{c['names'][m]} ({m})" for m in c["members"])
        lines.append(f"  - high: {members} -> canonical {c['canonical']}")
    for m in reconcile["medium"][:25]:
        members = " ~ ".join(f"{m['names'][x]} ({x})" for x in m["members"])
        lines.append(f"  - medium: {members}")
    lines.append("")

    lines.append("## Validation\n")
    if problems:
        lines.append(f"- {len(problems)} record(s) failed schema validation:")
        for rid, errs in sorted(problems.items()):
            lines.append(f"  - {rid}: {'; '.join(errs)}")
    else:
        lines.append("- all records valid (or validator unavailable)")
    lines.append("")

    report_path = root / "coverage_report.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # review.json: validation failures + contested records + reconcile candidates.
    review = {
        "validation_failures": problems,
        "contested": [
            r["id"] for coll in ("edges", "tenures", "persons")
            for r in store.all(coll) if r.get("confidence") == "contested" or r.get("status") == "contested"
        ],
        "merge_candidates": {
            "high": reconcile["high"],
            "medium": reconcile["medium"],
        },
        "note": "Provisional review queue. merge_candidates.high are auto-mergeable with "
                "--apply-merges; medium pairs need human/teacher confirmation.",
    }
    review_path = root / "review.json"
    review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {"report": report_path, "review": review_path}
