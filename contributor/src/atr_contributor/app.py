"""FastAPI app for the page-centric review tool.

A wide split view: the raw scanned page on the left (with a bbox overlay of the assigned
photos) and the page's parsed sequences on the right. The teacher re-parses a page (live
preview), edits the interpretation as Refinements at any scope, commits, and reviews each
technique. Re-parsing runs the ingestion in-process (see /api/reparse, added next).
"""

from __future__ import annotations

from pathlib import Path

import cv2
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from atr_ingest import captions as _captions
from atr_ingest.books import discover_books
from atr_ingest.cli import BOOKS_DIR
from atr_ingest.pipeline import parse_page
from atr_ingest.render import render_page
from atr_ingest.structure import section_for
from schema.contribution import Provenance
from schema.refinement import Refinement, RefinementStore, Scope, make_id

from .store import PROCESSED, REFINEMENTS, Store


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

    @app.get("/api/page/{book}/{page}")
    def page(book: str, page: int):
        if book not in books:
            raise HTTPException(404, "unknown book")
        sec = section_for(book, page, store.refs)
        return {"book": book, "page": page,
                "raw_page_url": f"/api/page-image/{book}/{page}.png",
                "section": {"context": sec.context, "kind": sec.kind, "weapon": sec.weapon,
                            "form": sec.form, "note": sec.note},
                "techniques": store.for_page(book, page),
                "content_pages": store.content_pages(book)}

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

    @app.get("/")
    def index():
        return FileResponse(str(WEB / "index.html"))

    @app.get("/healthz")
    def healthz():
        return JSONResponse({"ok": True})

    return app
