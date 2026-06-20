"""Taxonomy + review store.

Reads the provisional corpus (techniques.json, keyframes.json) and reads/writes the
teacher's reviews (reviews.json). Reviews never mutate the provisional records; they are
upserted as dated contribution events keyed by (technique, teacher). A review may also
carry a corrected keyframe sequence (images added/removed/reordered, with captions).
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
REVIEWS = TAXO / "reviews.json"
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


def img_url(image: str | None) -> str | None:
    """Map a repo-relative processed-image path to the /img static mount."""
    if not image:
        return None
    try:
        rel = Path(image).resolve().relative_to(PROCESSED.resolve())
    except ValueError:
        marker = "resources/books/processed/"
        rel = image.split(marker, 1)[1] if marker in image else image
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
        self.reviews = _load(REVIEWS, [])
        self._rev: dict[tuple[str, str], dict] = {
            (r["technique"], r["reviewed_by"]): r for r in self.reviews
        }

    # -- reads -------------------------------------------------------------
    def original_keyframes(self, tid: str) -> list[dict]:
        """The provisional keyframe sequence as {image, caption}."""
        out = []
        for k in self._kf.get(tid, []):
            out.append({"image": k.get("image"), "img": img_url(k.get("image")),
                        "caption": "", "step_index": k.get("step_index")})
        return out

    def review_for(self, tid: str) -> dict | None:
        return self._rev.get((tid, self.reviewer))

    def detail(self, tid: str) -> dict | None:
        tech = self._tech_by_id.get(tid)
        if not tech:
            return None
        review = self.review_for(tid)
        # effective sequence: the review's corrected one if present, else the original
        if review and review.get("keyframes"):
            seq = [{"image": k.get("image"), "img": img_url(k.get("image")),
                    "caption": k.get("caption", "")} for k in review["keyframes"]]
        else:
            seq = self.original_keyframes(tid)
        return {"technique": tech, "keyframes": seq, "review": review,
                "available": self.book_images(tech.get("source", {}).get("book"))}

    def book_images(self, book: str | None) -> list[dict]:
        """All processed images for a book, for the add-image picker."""
        if not book:
            return []
        root = PROCESSED / book
        if not root.exists():
            return []
        out = []
        for p in sorted(root.rglob("*.png")):
            rel = p.relative_to(PROCESSED)
            out.append({"image": f"resources/books/processed/{rel}",
                        "img": f"/img/{rel}", "page": rel.parts[1] if len(rel.parts) > 1 else ""})
        return out

    def queue(self) -> list[dict]:
        out = []
        for t in self.techniques:
            r = self._rev.get((t["id"], self.reviewer))
            out.append({
                "id": t["id"],
                "caption": (t.get("raw_caption") or t.get("name_romaji") or t["id"]),
                "book": t.get("source", {}).get("book"),
                "page": t.get("source", {}).get("pdf_page"),
                "verdict": r["verdict"] if r else None,
            })
        return out

    def next_unreviewed(self, after: str | None = None) -> str | None:
        ids = self._tech_order
        start = (ids.index(after) + 1) if after in self._tech_by_id and after else 0
        for tid in ids[start:] + ids[:start]:
            if (tid, self.reviewer) not in self._rev:
                return tid
        return None

    def progress(self) -> dict:
        total = len(self.techniques)
        mine = [r for r in self.reviews if r["reviewed_by"] == self.reviewer]
        by = defaultdict(int)
        for r in mine:
            by[r["verdict"]] += 1
        return {"total": total, "reviewed": len(mine), "by_verdict": dict(by),
                "reviewer": self.reviewer, "reviewer_name": self.reviewer_name}

    # -- write -------------------------------------------------------------
    def _norm_keyframes(self, payload: dict) -> list[dict] | None:
        if "keyframes" not in payload or payload["keyframes"] is None:
            return None
        seq = []
        for k in payload["keyframes"]:
            img = (k or {}).get("image")
            if not img:
                continue
            seq.append({"image": img, "caption": (k.get("caption") or "").strip()})
        return seq

    def save(self, tid: str, payload: dict) -> dict:
        if tid not in self._tech_by_id:
            raise KeyError(tid)
        slots = payload.get("slots") or {}
        record = {
            "id": f"review:{tid}:{self.reviewer}",
            "technique": tid,
            "verdict": payload.get("verdict", "confirmed"),
            "name_romaji": payload.get("name_romaji") or None,
            "name_native": payload.get("name_native") or None,
            "slots": {
                "attack": slots.get("attack") or None,
                "technique": slots.get("technique") or None,
                "direction": slots.get("direction") or None,
                "form": [f for f in slots.get("form", []) if f],
            },
            "keyframes": self._norm_keyframes(payload),
            "note": payload.get("note") or None,
            "reviewed_by": self.reviewer,
            "reviewed_by_name": self.reviewer_name,
            "date": _date.today().isoformat(),
            "status": "reviewed",
        }
        key = (tid, self.reviewer)
        if key in self._rev:
            idx = self.reviews.index(self._rev[key])
            self.reviews[idx] = record
        else:
            self.reviews.append(record)
        self._rev[key] = record
        _write_atomic(REVIEWS, self.reviews)
        return record
