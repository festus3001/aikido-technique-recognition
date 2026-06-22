"""FastAPI app for the page-centric review tool.

A wide split view: the raw scanned page on the left (with a bbox overlay of the assigned
photos) and the page's parsed sequences on the right. The teacher re-parses a page (live
preview), edits the interpretation as Refinements at any scope, commits, and reviews each
technique. Re-parsing runs the ingestion in-process (see /api/reparse, added next).
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import cv2
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from atr_ingest import captions as _captions
from atr_ingest.books import discover_books
from atr_ingest.cli import BOOKS_DIR
from atr_ingest.pipeline import parse_page, scan_volume_images
from atr_ingest.render import render_page
from atr_ingest.structure import section_for
from atr_ingest.textblocks import extract_text_blocks
from atr_ingest.translate import DEFAULT_MODEL, load_glossary, translate as _translate
from schema.contribution import Provenance
from schema.refinement import Refinement, RefinementStore, Scope, make_id

from datetime import date as _date

from .store import PROCESSED, REFINEMENTS, REPO_ROOT, Store


def _section_dict(sec) -> dict:
    return {"context": sec.context, "kind": sec.kind, "weapon": sec.weapon,
            "form": sec.form, "note": sec.note}


def _inflight(items: list[dict], author: str) -> list[Refinement]:
    """Build unsaved Refinement objects from the UI's in-flight overrides (for live preview)."""
    out = []
    for it in items or []:
        scope = Scope(level=it["level"], selector=it.get("selector", {}))
        payload = it.get("payload", {})
        out.append(Refinement(id=make_id(scope, it["target"], payload, author=author),
                              scope=scope, target=it["target"], payload=payload,
                              provenance=Provenance(author=author, basis="teacher"),
                              status="provisional"))
    return out

WEB = Path(__file__).resolve().parent / "web"


def create_app(reviewer: str, reviewer_name: str | None = None) -> FastAPI:
    app = FastAPI(title="ATR review")
    store = Store(reviewer, reviewer_name)
    books = {b["id"]: (b, pdf) for b, pdf in discover_books(BOOKS_DIR)}
    preview_crops: dict[str, bytes] = {}   # "{book}:{page}:{idx}" -> PNG bytes (live re-parse)
    image_jobs: dict[str, dict] = {}       # book -> {status, done, total} for the volume image scan

    def _index_path(b: str) -> Path:
        return PROCESSED / b / "_pages" / "images.json"

    def _load_index(b: str) -> dict | None:
        p = _index_path(b)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    SCAN_DPI = 150          # 4x faster than 300; detection is dpi-robust
    SCALE = 300 // SCAN_DPI  # store bboxes in 300-dpi space (matches the page image + keyframes)

    def _build_index(b: str):
        bk, pdf = books[b]
        total = bk.get("pages") or 0
        image_jobs[b] = {"status": "running", "done": 0, "total": total}

        def prog(done, tot):
            image_jobs[b]["done"] = done
        images = scan_volume_images(pdf, total, dpi=SCAN_DPI, progress=prog)
        for im in images:
            im["bbox"] = [v * SCALE for v in im["bbox"]]   # -> 300-dpi space
        data = {"book": b, "total_images": len(images), "images": images,
                "pages": sorted({im["page"] for im in images})}
        p = _index_path(b)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        image_jobs[b] = {"status": "done", "done": total, "total": total}

    if PROCESSED.exists():
        app.mount("/img", StaticFiles(directory=str(PROCESSED)), name="img")

    # -- existing technique-level review API --------------------------------
    @app.get("/api/progress")
    def progress():
        return store.progress()

    @app.get("/api/queue")
    def queue():
        return store.queue()

    @app.get("/api/technique/{tid}")
    def technique(tid: str):
        d = store.detail(tid)
        if not d:
            raise HTTPException(404, "unknown technique")
        return d

    @app.get("/api/next")
    def nxt(after: str | None = None):
        return {"id": store.next_unreviewed(after)}

    @app.post("/api/review/{tid}")
    async def review(tid: str, payload: dict):
        try:
            return store.save(tid, payload)
        except KeyError:
            raise HTTPException(404, "unknown technique")

    # -- page-centric API ---------------------------------------------------
    @app.get("/api/books")
    def list_books():
        out = []
        for bid, (b, _pdf) in books.items():
            pages = store.content_pages(bid)
            out.append({"id": bid, "full_title": b.get("full_title"), "volume": b.get("volume"),
                        "pages": b.get("pages"), "content_pages": pages,
                        "page_span": [pages[0], pages[-1]] if pages else None})
        out.sort(key=lambda x: x.get("volume") or 0)
        return out

    @app.get("/api/images/{book}")
    def images(book: str):
        """The absolute volume image index (built once, cached). Returns ready=False with
        progress while a background scan runs."""
        if book not in books:
            raise HTTPException(404, "unknown book")
        idx = _load_index(book)
        if idx:
            return {"ready": True, "total_images": idx["total_images"], "pages": idx["pages"]}
        job = image_jobs.get(book)
        if not job or job.get("status") != "running":
            threading.Thread(target=_build_index, args=(book,), daemon=True).start()
            job = image_jobs.get(book, {"status": "running", "done": 0,
                                        "total": books[book][0].get("pages") or 0})
        return {"ready": False, "done": job.get("done", 0), "total": job.get("total", 0)}

    @app.get("/api/page/{book}/{page}")
    def page(book: str, page: int):
        if book not in books:
            raise HTTPException(404, "unknown book")
        sec = section_for(book, page, store.refs)
        techs = store.for_page(book, page)
        # absolute image numbers for this page, from the cached volume index. Match a keyframe
        # to its index region by center-containment (index is 150->300 scaled, so not pixel-exact).
        idx = _load_index(book)
        regions = []
        if idx:
            page_imgs = [im for im in idx["images"] if im["page"] == page]

            def abs_for(bbox):
                if not bbox:
                    return None
                cx, cy = bbox[0] + bbox[2] / 2, bbox[1] + bbox[3] / 2
                for im in page_imgs:
                    x, y, w, h = im["bbox"]
                    if x <= cx <= x + w and y <= cy <= y + h:
                        return im["n"]
                return None

            assigned_ns = set()
            for t in techs:
                for k in t["keyframes"]:
                    k["abs_n"] = abs_for(k.get("source", {}).get("bbox"))
                    if k["abs_n"] is not None:
                        assigned_ns.add(k["abs_n"])
            regions = [{"n": im["n"], "bbox": im["bbox"], "granularity": im["granularity"],
                        "assigned": im["n"] in assigned_ns} for im in page_imgs]
        return {"book": book, "page": page,
                "raw_page_url": f"/api/page-image/{book}/{page}.png",
                "section": {"context": sec.context, "kind": sec.kind, "weapon": sec.weapon,
                            "form": sec.form, "note": sec.note},
                "techniques": techs, "regions": regions,
                "textblocks": store.textblocks_for(book, page),
                "content_pages": store.content_pages(book)}

    @app.post("/api/textblocks/{book}/{page}")
    def capture_text(book: str, page: int, payload: dict | None = None):
        """OCR every text block on the page (Tesseract layout); optionally translate the
        Japanese ones (local glossary-tuned). Replaces this page's stored blocks."""
        if book not in books:
            raise HTTPException(404, "unknown book")
        do_tr = bool((payload or {}).get("translate"))
        bk = books[book][0]
        prov = {"performer": bk.get("performer"), "performer_name": bk.get("performer_name"),
                "era": bk.get("era"), "medium": "book", "recording": book, "lineage": bk.get("lineage")}
        img = render_page(books[book][1], page, 300)
        glossary = load_glossary(store=store.refs) if do_tr else None
        recs = []
        for i, blk in enumerate(extract_text_blocks(img), start=1):
            rec = {"id": f"text:{book}-p{page}-b{i}", "book": book, "page": page, "block": i,
                   "bbox": blk["bbox"], "text": blk["text"], "lang": blk["lang"], "conf": blk["conf"],
                   "translation": None, "translation_model": None, "terms_used": [],
                   "source": {"book": book, "title": bk.get("full_title"), "pdf_page": page},
                   "provenance": prov, "status": "provisional", "retrieved": _date.today().isoformat()}
            if do_tr and blk["lang"] == "ja":
                en, used = _translate(blk["text"], glossary)
                rec.update(translation=en, translation_model=DEFAULT_MODEL, terms_used=used)
            recs.append(rec)
        store.replace_textblocks(book, page, recs)
        return {"textblocks": store.textblocks_for(book, page)}

    @app.post("/api/textblock/correct")
    def correct_text(payload: dict):
        """Teacher correction of a block's OCR text and/or translation -> Refinements."""
        sel = {"book": payload["book"], "page": payload["page"], "block": payload["block"]}
        prov = Provenance(author=reviewer, basis="teacher", note=reviewer_name or None)
        if payload.get("text") is not None:
            store.refs.add("page", "text.ocr", {"text": payload["text"]}, prov, selector=sel)
        if payload.get("translation") is not None:
            store.refs.add("page", "text.translation", {"text": payload["translation"]}, prov, selector=sel)
        store.refs.save()
        return {"ok": True}

    @app.post("/api/textblock/retranslate")
    def retranslate_text(payload: dict):
        """Re-translate one block with the current glossary (machine output, stored on the block)."""
        b, p, bl = payload["book"], payload["page"], payload["block"]
        from schema.refinement import resolve
        rec = next((r for r in store.textblocks if r["book"] == b and r["page"] == p and r["block"] == bl), None)
        if not rec:
            raise HTTPException(404, "no such block")
        ocr = resolve("text.ocr", {"book": b, "page": p, "block": bl}, store.refs, base=None)
        text = ocr["text"] if ocr else rec["text"]
        en, used = _translate(text, load_glossary(store=store.refs))
        store.update_textblock(b, p, bl, translation=en, translation_model=DEFAULT_MODEL, terms_used=used)
        return {"translation": en, "terms_used": used}

    # -- live re-parse (preview) -- plain `def` so Starlette offloads OCR to a threadpool --
    @app.post("/api/reparse/{book}/{page}")
    def reparse(book: str, page: int, payload: dict | None = None):
        if book not in books:
            raise HTTPException(404, "unknown book")
        extra = _inflight((payload or {}).get("refinements", []), reviewer)
        rstore = RefinementStore(path=REFINEMENTS, extra=extra)
        _captions.apply_lexicon(rstore)
        try:
            pp = parse_page(books[book][1], page, books[book][0], store=rstore,
                            write_keyframes=False)
        finally:
            _captions.reset_lexicon()
        # clear prior preview crops for this page, cache the new ones, attach urls
        for k in [k for k in preview_crops if k.startswith(f"{book}:{page}:")]:
            preview_crops.pop(k, None)
        for i, crop in enumerate(pp.crops or []):
            ok, buf = cv2.imencode(".png", crop)
            if ok:
                preview_crops[f"{book}:{page}:{i}"] = buf.tobytes()
            pp.keyframes[i]["img"] = f"/api/preview-crop/{book}/{page}/{i}.png"
        by_tid: dict[str, list] = {}
        for kf in pp.keyframes:
            by_tid.setdefault(kf["technique"], []).append(kf)
        techs = [{"technique": t, "keyframes": by_tid.get(t["id"], []), "review": None}
                 for t in pp.techniques]
        return {"book": book, "page": page, "preview": True,
                "section": _section_dict(pp.section) if pp.section else None,
                "page_size": pp.page_size, "techniques": techs,
                "captions": pp.captions, "regions": [list(r) for r in pp.regions]}

    @app.get("/api/preview-crop/{book}/{page}/{idx}.png")
    def preview_crop(book: str, page: int, idx: int):
        data = preview_crops.get(f"{book}:{page}:{idx}")
        if data is None:
            raise HTTPException(404, "no preview crop")
        return Response(content=data, media_type="image/png")

    @app.get("/api/page-image/{book}/{page}.png")
    def page_image(book: str, page: int):
        if book not in books:
            raise HTTPException(404, "unknown book")
        cache = PROCESSED / book / "_pages" / f"p{page}.png"
        if not cache.exists():
            cache.parent.mkdir(parents=True, exist_ok=True)
            img = render_page(books[book][1], page, 300)
            cv2.imwrite(str(cache), img)
        return FileResponse(str(cache), media_type="image/png")

    @app.post("/api/region-crop")
    def region_crop(payload: dict):
        """Crop one indexed image (book, page, absolute n) to a file and return its path/url.
        Lets an image dragged from the page -- including an un-extracted one -- become a real
        keyframe in a sequence."""
        book, page, n = payload["book"], int(payload["page"]), int(payload["n"])
        if book not in books:
            raise HTTPException(404, "unknown book")
        idx = _load_index(book)
        im = next((x for x in (idx or {}).get("images", []) if x["n"] == n and x["page"] == page), None)
        if not im:
            raise HTTPException(404, "no such image")
        out = PROCESSED / book / "_regions" / f"p{page}-n{n}.png"
        if not out.exists():
            out.parent.mkdir(parents=True, exist_ok=True)
            cache = PROCESSED / book / "_pages" / f"p{page}.png"
            img = cv2.imread(str(cache)) if cache.exists() else render_page(books[book][1], page, 300)
            x, y, w, h = im["bbox"]
            cv2.imwrite(str(out), img[max(0, y):y + h, max(0, x):x + w])
        rel = out.relative_to(PROCESSED)
        return {"image": f"resources/books/processed/{rel}", "img": f"/img/{rel}", "n": n}

    @app.post("/api/commit-page/{book}/{page}")
    def commit_page(book: str, page: int, payload: dict | None = None):
        if book not in books:
            raise HTTPException(404, "unknown book")
        # 1. persist the in-flight overrides so the parse is reproducible (batch + future re-parse)
        for it in (payload or {}).get("refinements", []):
            store.refs.add(it["level"], it["target"], it.get("payload", {}),
                           Provenance(author=reviewer, basis="teacher", note=reviewer_name or None),
                           selector=it.get("selector"))
        store.refs.save()
        # 2. drop stale crop dirs for this page, then parse committing crops to disk
        for d in (PROCESSED / book).glob(f"p{page}-*"):
            if d.is_dir():
                for f in d.glob("*"):
                    f.unlink()
                d.rmdir()
        _captions.apply_lexicon(store.refs)
        try:
            pp = parse_page(books[book][1], page, books[book][0], store=store.refs,
                            write_keyframes=True, processed_root=PROCESSED, repo_root=REPO_ROOT,
                            retrieved=_date.today().isoformat())
        finally:
            _captions.reset_lexicon()
        # 3. replace the page's records
        store.commit_page(book, page, pp.techniques, pp.keyframes)
        for k in [k for k in preview_crops if k.startswith(f"{book}:{page}:")]:
            preview_crops.pop(k, None)
        return {"committed": len(pp.techniques), "keyframes": len(pp.keyframes),
                "section": _section_dict(pp.section) if pp.section else None}

    # -- Refinement CRUD (one API for every scope/target) --------------------
    @app.get("/api/refinements")
    def list_refinements(target: str | None = None, book: str | None = None,
                         page: int | None = None, technique: str | None = None):
        unit = {}
        if book:
            unit["book"] = book
        if page is not None:
            unit["page"] = page
        if technique:
            unit["technique"] = technique
        return [r.to_dict() for r in store.refs.query(target=target, unit=unit or None)]

    @app.post("/api/refinements")
    def add_refinement(payload: dict):
        r = store.refs.add(payload["level"], payload["target"], payload.get("payload", {}),
                           Provenance(author=reviewer, basis="teacher", note=reviewer_name or None),
                           selector=payload.get("selector"),
                           status=payload.get("status", "provisional"))
        store.refs.save()
        return r.to_dict()

    @app.post("/api/refinements/delete")
    def delete_refinement(payload: dict):
        store.refs.remove(payload["id"])
        store.refs.save()
        return {"ok": True}

    @app.post("/api/refinements/confirm")
    def confirm_refinement(payload: dict):
        r = store.refs.get(payload["id"])
        if not r:
            raise HTTPException(404, "unknown refinement")
        r.status = "confirmed"
        store.refs.save()
        return r.to_dict()

    @app.get("/api/sections/{book}")
    def sections(book: str):
        from atr_ingest.structure import _MAPS
        seed = [{"start": s, "end": e, "context": sec.context, "kind": sec.kind,
                 "weapon": sec.weapon, "form": sec.form, "note": sec.note}
                for s, e, sec in _MAPS.get(book, [])]
        refs = [r.to_dict() for r in store.refs.by_target("section")
                if r.scope.selector.get("book") == book and r.status != "retired"]
        return {"seed": seed, "refinements": refs}

    @app.get("/")
    def index():
        return FileResponse(str(WEB / "index.html"))

    @app.get("/healthz")
    def healthz():
        return JSONResponse({"ok": True})

    return app
