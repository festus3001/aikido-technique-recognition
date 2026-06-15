"""ATR contributor backend (FastAPI). Serves the model; records contributions.

Run: uvicorn app.main:app --reload
Routes are stubs; a coding agent wires them to schema/ and the trained model.
"""
from fastapi import FastAPI

app = FastAPI(title="ATR Contributor API")


@app.get("/health")
def health():
    return {"status": "ok"}

# TODO(agent): include routers from app.routes (parse, contribution, clip, technique).
