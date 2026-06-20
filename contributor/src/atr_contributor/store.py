"""Taxonomy + ratification store.

Reads the provisional corpus (techniques.json, keyframes.json) and reads/writes the
teacher's corrections (ratifications.json). Corrections never mutate the provisional
records; they are upserted as dated contribution events keyed by (technique, teacher).
"""

from __future__ import annotations

import json
import os
import tempfile
from collections import defaultdict
from datetime import date as _date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TAXO = REPO_ROOT / "data" / "taxonomy"
TECHNIQUES = TAXO / "techniques.json"
KEYFRAMES = TAXO / "keyframes.json"
RATIFICATIONS = TAXO / "ratifications.json"
PROCESSED = REPO_ROOT / "resources" / "books" / "processed"


def _load(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _write_atomic(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def img_url(keyframe: dict) -> str | None:
    """Map a keyframe's repo-relative image path to the /img static mount."""
    raw = keyframe.get("image")
    if not raw:
        return None
    try:
        rel = Path(raw).resolve().relative_to(PROCESSED.resolve())
    except ValueError:
        marker = "resources/books/processed/"
        rel = raw.split(marker, 1)[1] if marker in raw else raw
    return f"/img/{rel}"


class Store:
    def __init__(self, reviewer: str, reviewer_name: str | None = None):
        self.reviewer = reviewer
        self.reviewer_name = reviewer_name
        self.techniques = _load(TECHNIQUES, [])
        self.keyframes = _load(KEYFRAMES, [])
        self._kf: dict[str, list] = defaultdict(list)
        for k in self.keyframes:
            self._kf[k["technique"]].append(k)
        for v in self._kf.values():
            v.sort(key=lambda k: k.get("step_index", 0))
        self._tech_order = [t["id"] for t in self.techniques]
        self._tech_by_id = {t["id"]: t for t in self.techniques}
        self.ratifications = _load(RATIFICATIONS, [])
        self._rat: dict[tuple[str, str], dict] = {
            (r["technique"], r["ratified_by"]): r for r in self.ratifications
        }

    # -- reads -------------------------------------------------------------
    def keyframes_for(self, tid: str) -> list[dict]:
        return self._kf.get(tid, [])

    def ratification_for(self, tid: str) -> dict | None:
        return self._rat.get((tid, self.reviewer))

    def detail(self, tid: str) -> dict | None:
        tech = self._tech_by_id.get(tid)
        if not tech:
            return None
        kfs = [{**k, "img": img_url(k)} for k in self.keyframes_for(tid)]
        return {"technique": tech, "keyframes": kfs, "ratification": self.ratification_for(tid)}

    def queue(self) -> list[dict]:
        """Lightweight nav list: id, display caption, ratified verdict (if any)."""
        out = []
        for t in self.techniques:
            r = self._rat.get((t["id"], self.reviewer))
            out.append({
                "id": t["id"],
                "caption": (t.get("raw_caption") or t.get("name_romaji") or t["id"]),
                "book": t.get("source", {}).get("book"),
                "verdict": r["verdict"] if r else None,
            })
        return out

    def next_unreviewed(self, after: str | None = None) -> str | None:
        ids = self._tech_order
        start = (ids.index(after) + 1) if after in self._tech_by_id and after else 0
        for tid in ids[start:] + ids[:start]:
            if (tid, self.reviewer) not in self._rat:
                return tid
        return None

    def progress(self) -> dict:
        total = len(self.techniques)
        mine = [r for r in self.ratifications if r["ratified_by"] == self.reviewer]
        by = defaultdict(int)
        for r in mine:
            by[r["verdict"]] += 1
        return {"total": total, "reviewed": len(mine), "by_verdict": dict(by),
                "reviewer": self.reviewer, "reviewer_name": self.reviewer_name}

    # -- write -------------------------------------------------------------
    def save(self, tid: str, payload: dict) -> dict:
        if tid not in self._tech_by_id:
            raise KeyError(tid)
        record = {
            "id": f"ratify:{tid}:{self.reviewer}",
            "technique": tid,
            "verdict": payload.get("verdict", "confirmed"),
            "name_romaji": payload.get("name_romaji") or None,
            "name_native": payload.get("name_native") or None,
            "slots": {
                "attack": (payload.get("slots") or {}).get("attack") or None,
                "technique": (payload.get("slots") or {}).get("technique") or None,
                "direction": (payload.get("slots") or {}).get("direction") or None,
                "form": [f for f in (payload.get("slots") or {}).get("form", []) if f],
            },
            "note": payload.get("note") or None,
            "ratified_by": self.reviewer,
            "ratified_by_name": self.reviewer_name,
            "date": _date.today().isoformat(),
            "status": "ratified",
        }
        key = (tid, self.reviewer)
        if key in self._rat:
            idx = self.ratifications.index(self._rat[key])
            self.ratifications[idx] = record
        else:
            self.ratifications.append(record)
        self._rat[key] = record
        _write_atomic(RATIFICATIONS, self.ratifications)
        return record
