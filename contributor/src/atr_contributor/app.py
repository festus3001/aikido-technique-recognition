"""FastAPI app for the teacher review loop.

One page, served at /. The teacher sees a technique's step photos and corrects the
name + slots, edits the image sequence, and adds a deep-layer note; each save writes
to reviews.json.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .store import PROCESSED, Store

WEB = Path(__file__).resolve().parent / "web"


def create_app(reviewer: str, reviewer_name: str | None = None) -> FastAPI:
    app = FastAPI(title="ATR review")
    store = Store(reviewer, reviewer_name)

    if PROCESSED.exists():
        app.mount("/img", StaticFiles(directory=str(PROCESSED)), name="img")

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

    @app.get("/")
    def index():
        return FileResponse(str(WEB / "index.html"))

    @app.get("/healthz")
    def healthz():
        return JSONResponse({"ok": True})

    return app
