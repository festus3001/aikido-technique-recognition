"""Taxonomy + review store.

Reads the provisional corpus (techniques.json, keyframes.json) and reads/writes the
teacher's corrections as **Refinements** (schema/refinement.py), the project's one
correction primitive. A teacher review is a set of technique-scope Refinements --
`name`, `parse.slots`, `keyframe.sequence`, `verdict`, `note` -- authored by the
reviewer. The corpus is never mutated by review; corrections layer on top and resolve.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path

from schema.contribution import Provenance
from schema.refinement import RefinementStore

REPO_ROOT = Path(__file__).resolve().parents[3]
TAXO = REPO_ROOT / "data" / "taxonomy"
TECHNIQUES = TAXO / "techniques.json"
KEYFRAMES = TAXO / "keyframes.json"
TEXTBLOCKS = TAXO / "textblocks.json"
REFINEMENTS = REPO_ROOT / "data" / "refinements.json"
PROCESSED = REPO_ROOT / "resources" / "books" / "processed"

# the technique-scope targets that make up a review
REVIEW_TARGETS = ("name", "parse.slots", "keyframe.sequence", "verdict", "note")


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
        self.refs = RefinementStore(path=REFINEMENTS)
        self.textblocks = _load(TEXTBLOCKS, [])

    # -- refinement access ----------------------------------------------------
    def _my_ref(self, tid: str, target: str):
        """This reviewer's active Refinement for (technique, target), if any."""
        for r in self.refs.by_target(target):
            if (r.status != "retired" and r.scope.selector.get("technique") == tid
                    and r.provenance.author == self.reviewer):
                return r
        return None

    def review_for(self, tid: str) -> dict | None:
        """Reconstruct this reviewer's review of a technique from their Refinements."""
        v = self._my_ref(tid, "verdict")
        if not v:
            return None
        name = self._my_ref(tid, "name")
        slots = self._my_ref(tid, "parse.slots")
        kf = self._my_ref(tid, "keyframe.sequence")
        note = self._my_ref(tid, "note")
        return {
            "verdict": v.payload.get("verdict"),
            "name_romaji": (name.payload.get("romaji") if name else None),
            "name_native": (name.payload.get("native") if name else None),
            "slots": (slots.payload if slots else None),
            "keyframes": (kf.payload.get("sequence") if kf else None),
            "note": (note.payload.get("text") if note else None),
            "date": v.provenance.date,
        }

    # -- reads ----------------------------------------------------------------
    def original_keyframes(self, tid: str) -> list[dict]:
        return [{"image": k.get("image"), "img": img_url(k.get("image")),
                 "caption": "", "step_index": k.get("step_index")}
                for k in self._kf.get(tid, [])]

    def detail(self, tid: str) -> dict | None:
        tech = self._tech_by_id.get(tid)
        if not tech:
            return None
        review = self.review_for(tid)
        if review and review.get("keyframes"):
            seq = [{"image": k.get("image"), "img": img_url(k.get("image")),
                    "caption": k.get("caption", "")} for k in review["keyframes"]]
        else:
            seq = self.original_keyframes(tid)
        return {"technique": tech, "keyframes": seq, "review": review,
                "available": self.book_images(tech.get("source", {}).get("book"))}

    def book_images(self, book: str | None) -> list[dict]:
        if not book:
            return []
        root = PROCESSED / book
        if not root.exists():
            return []
        out = []
        for p in sorted(root.rglob("*.png")):
            rel = p.relative_to(PROCESSED)
            if rel.parts[1:2] and rel.parts[1].startswith("_"):
                continue   # skip cache dirs like _pages/
            out.append({"image": f"resources/books/processed/{rel}",
                        "img": f"/img/{rel}", "page": rel.parts[1] if len(rel.parts) > 1 else ""})
        return out

    def for_page(self, book: str, page: int) -> list[dict]:
        """The committed techniques on one page, each with its keyframes (img + bbox) and review."""
        out = []
        for t in self.techniques:
            s = t.get("source", {})
            if s.get("book") == book and s.get("pdf_page") == page:
                kfs = [{**k, "img": img_url(k.get("image"))} for k in self._kf.get(t["id"], [])]
                out.append({"technique": t, "keyframes": kfs, "review": self.review_for(t["id"])})
        return out

    # -- text blocks (prose / the books' English) -----------------------------
    def textblocks_for(self, book: str, page: int) -> list[dict]:
        """The page's text blocks, with any teacher text/translation corrections applied."""
        from schema.refinement import resolve
        out = []
        for r in self.textblocks:
            if r["book"] == book and r["page"] == page:
                unit = {"book": book, "page": page, "block": r["block"]}
                ocr = resolve("text.ocr", unit, self.refs, base=None)
                tr = resolve("text.translation", unit, self.refs, base=None)
                out.append({**r,
                            "text": ocr["text"] if ocr else r["text"],
                            "translation": tr["text"] if tr else r.get("translation"),
                            "corrected": bool(ocr or tr)})
        out.sort(key=lambda r: r["block"])
        return out

    def replace_textblocks(self, book: str, page: int, records: list[dict]) -> None:
        self.textblocks = [r for r in self.textblocks
                           if not (r["book"] == book and r["page"] == page)] + records
        self._save_textblocks()

    def update_textblock(self, book: str, page: int, block: int, **fields) -> None:
        for r in self.textblocks:
            if r["book"] == book and r["page"] == page and r["block"] == block:
                r.update(fields)
        self._save_textblocks()

    def _save_textblocks(self) -> None:
        _write_atomic(TEXTBLOCKS, sorted(self.textblocks, key=lambda r: (r["book"], r["page"], r["block"])))

    def content_pages(self, book: str) -> list[int]:
        return sorted({t["source"]["pdf_page"] for t in self.techniques
                       if t.get("source", {}).get("book") == book and t["source"].get("pdf_page")})

    def queue(self) -> list[dict]:
        out = []
        for t in self.techniques:
            r = self._my_ref(t["id"], "verdict")
            out.append({"id": t["id"],
                        "caption": (t.get("raw_caption") or t.get("name_romaji") or t["id"]),
                        "book": t.get("source", {}).get("book"),
                        "page": t.get("source", {}).get("pdf_page"),
                        "verdict": (r.payload.get("verdict") if r else None)})
        return out

    def next_unreviewed(self, after: str | None = None) -> str | None:
        ids = self._tech_order
        start = (ids.index(after) + 1) if after in self._tech_by_id and after else 0
        for tid in ids[start:] + ids[:start]:
            if self._my_ref(tid, "verdict") is None:
                return tid
        return None

    def progress(self) -> dict:
        by = defaultdict(int)
        reviewed = 0
        for t in self.techniques:
            r = self._my_ref(t["id"], "verdict")
            if r:
                reviewed += 1
                by[r.payload.get("verdict")] += 1
        return {"total": len(self.techniques), "reviewed": reviewed, "by_verdict": dict(by),
                "reviewer": self.reviewer, "reviewer_name": self.reviewer_name}

    # -- page commit (re-parse result replaces the page's records) ------------
    def commit_page(self, book: str, page: int, techs: list[dict], kfs: list[dict]) -> None:
        """Replace this page's techniques/keyframes with a freshly parsed set, then reload."""
        def other(rec):
            s = rec.get("source", {})
            return not (s.get("book") == book and s.get("pdf_page") == page)
        techniques = [t for t in _load(TECHNIQUES, []) if other(t)] + techs
        keyframes = [k for k in _load(KEYFRAMES, []) if other(k)] + kfs
        techniques.sort(key=lambda r: r["id"])   # match the ingest store's canonical order
        keyframes.sort(key=lambda r: r["id"])    # so an idempotent commit produces no diff
        _write_atomic(TECHNIQUES, techniques)
        _write_atomic(KEYFRAMES, keyframes)
        self.__init__(self.reviewer, self.reviewer_name)   # refresh in-memory indices

    # -- write ----------------------------------------------------------------
    def save(self, tid: str, payload: dict) -> dict:
        if tid not in self._tech_by_id:
            raise KeyError(tid)
        prov = lambda: Provenance(author=self.reviewer, basis="teacher",
                                  note=self.reviewer_name or None)
        sel = {"technique": tid}
        self.refs.add("technique", "verdict", {"verdict": payload.get("verdict", "confirmed")},
                      prov(), selector=sel)
        if payload.get("name_romaji") or payload.get("name_native"):
            self.refs.add("technique", "name",
                          {"romaji": payload.get("name_romaji") or None,
                           "native": payload.get("name_native") or None}, prov(), selector=sel)
        slots = payload.get("slots") or {}
        norm_slots = {"attack": slots.get("attack") or None,
                      "technique": slots.get("technique") or None,
                      "direction": slots.get("direction") or None,
                      "form": [f for f in slots.get("form", []) if f]}
        if any(v for v in (norm_slots["attack"], norm_slots["technique"],
                           norm_slots["direction"]) ) or norm_slots["form"]:
            self.refs.add("technique", "parse.slots", norm_slots, prov(), selector=sel)
        if payload.get("keyframes") is not None:
            seq = [{"image": k["image"], "caption": (k.get("caption") or "").strip()}
                   for k in payload["keyframes"] if k.get("image")]
            self.refs.add("technique", "keyframe.sequence", {"sequence": seq}, prov(), selector=sel)
        if payload.get("note"):
            self.refs.add("technique", "note", {"text": payload["note"]}, prov(), selector=sel)
        self.refs.save()
        return self.review_for(tid)
