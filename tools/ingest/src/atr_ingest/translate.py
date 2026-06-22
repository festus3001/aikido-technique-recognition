"""Local, glossary-tuned JP->EN translation for the book text blocks.

Runs entirely locally against Ollama. For a given Japanese passage it retrieves the aikido
glossary terms whose kanji appear in the text and injects them as exact term mappings, so
budo vocabulary translates correctly and consistently. The glossary is the tunable knowledge
(the RAG): grow/correct it (data/taxonomy/glossary.json) and re-translate -- no model retrain.
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
GLOSSARY_PATH = REPO_ROOT / "data" / "taxonomy" / "glossary.json"
OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "gemma3:12b"

_CJK = re.compile(r"[぀-ヿ㐀-鿿々]")


def load_glossary(path: Path = GLOSSARY_PATH, store=None) -> list[tuple[str, dict]]:
    """(kanji, term) pairs that carry both kanji and an English gloss, longest kanji first
    so specific multi-kanji terms match before their components. When a RefinementStore is
    given, teacher-added `glossary.term` refinements are folded on top (no rebuild needed)."""
    terms = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    pairs = [(k, t) for t in terms for k in t.get("kanji", []) if k and t.get("english")]
    if store is not None:
        for r in store.by_target("glossary.term"):
            if r.status == "retired":
                continue
            p = r.payload
            for k in p.get("kanji", []):
                if k and p.get("english"):
                    pairs.append((k, {"romaji": p.get("romaji", ""), "english": p["english"]}))
    pairs.sort(key=lambda kt: -len(kt[0]))
    return pairs


def retrieve(text: str, glossary: list[tuple[str, dict]]) -> list[dict]:
    """Glossary terms whose kanji appear in the passage (each once, specific-first)."""
    hits, seen = [], set()
    for kanji, t in glossary:
        if kanji in text and kanji not in seen:
            seen.add(kanji)
            hits.append({"kanji": kanji, "romaji": t["romaji"], "english": t["english"]})
    return hits


def is_japanese(text: str) -> bool:
    return bool(_CJK.search(text))


def _ollama(prompt: str, model: str, timeout: int) -> str:
    body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0.2}}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())["response"].strip()


def translate(text: str, glossary: list[tuple[str, dict]] | None = None,
              model: str = DEFAULT_MODEL, timeout: int = 180) -> tuple[str, list[str]]:
    """Translate one Japanese passage. Returns (english, [glossary kanji used])."""
    glossary = load_glossary() if glossary is None else glossary
    terms = retrieve(text, glossary)
    termlines = "\n".join(f"- {h['kanji']} = {h['english']} ({h['romaji']})" for h in terms)
    prompt = (
        "You are translating instructional text from a traditional aikido (合気道) manual "
        "into clear, accurate English.\n"
        + (f"Use these domain term translations exactly and consistently:\n{termlines}\n\n" if terms else "")
        + "Translate the Japanese below into natural English. For aikido technical terms "
          "(techniques, attacks, stances, weapons) give the romaji in parentheses on first use; "
          "do NOT romanize ordinary words. Output ONLY the English translation -- no preamble, "
          "notes, or the original text.\n\nJapanese:\n" + text
    )
    return _ollama(prompt, model, timeout), [h["kanji"] for h in terms]
