"""Build data/taxonomy/glossary.json -- the bilingual aikido term base.

Seeds from the project's curated lexicon (kanji, by slot) plus a downloaded selection of
public glossaries in resources/glossaries/raw/. Every term records its sources and is
provisional and teacher-correctable. This term base is the shared spine: the parser's
lexicon and the (coming) local translator's domain RAG both draw from it.

Run (atr-ingest env, for the curated core):
  conda run -n atr-ingest python tools/glossary/build.py
"""

from __future__ import annotations

import html
import json
import re
import subprocess
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "resources" / "glossaries" / "raw"
OUT = REPO / "data" / "taxonomy" / "glossary.json"
TODAY = date.today().isoformat()

CJK = re.compile(r"[぀-ヿ㐀-鿿々]")


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


# header keyword -> our category vocabulary
_CAT = [("attack", "attack"), ("grab", "attack"), ("strike", "attack"), ("hold", "attack"),
        ("technique", "technique"), ("throw", "technique"), ("pin", "technique"), ("control", "technique"),
        ("direction", "direction"),
        ("stance", "form"), ("posture", "form"), ("position", "form"), ("step", "form"),
        ("weapon", "weapon"), ("count", "count"), ("number", "count"),
        ("practice", "practice"), ("exercise", "practice"), ("body", "body"),
        ("general", "general"), ("term", "general")]


def cat_from_header(h: str) -> str | None:
    h = h.lower()
    for kw, cat in _CAT:
        if kw in h:
            return cat
    return None


def curated_core() -> list[dict]:
    """The verified project lexicon: romaji + kanji + slot category."""
    from atr_ingest import captions as c
    out = []
    for slot, table in (("technique", c.TECHNIQUES), ("attack", c.ATTACKS),
                        ("direction", c.DIRECTIONS), ("form", c.FORMS)):
        for canon in table:
            out.append({"romaji": canon.replace("-", " "), "kanji": list(c.KANJI.get(slot, {}).get(canon, [])),
                        "kana": [], "english": None, "category": slot, "source": "atr-lexicon"})
    return out


def parse_aikidude() -> list[dict]:
    """<strong>Romaji</strong> &#8211; 漢字 (かな): english, grouped under section headers."""
    t = (RAW / "aikidude.html").read_text(encoding="utf-8")
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", t, flags=re.S)
    terms, cur = [], None
    pat = re.compile(r"<h[1-6][^>]*>(.*?)</h[1-6]>"
                     r"|<strong>\s*(.*?)\s*</strong>\s*(?:&#8211;|&#8212;|–|—|-)\s*(.*?)(?=<br|</p)", re.S)
    for m in pat.finditer(t):
        if m.group(1) is not None:
            cur = cat_from_header(re.sub(r"<[^>]+>", "", m.group(1))) or cur
            continue
        romaji = html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
        rest = html.unescape(re.sub(r"<[^>]+>", "", m.group(3))).strip()
        # strip a leading section word that bled into the romaji ("Attacks Dori" -> "Dori")
        romaji = re.sub(r"^(attacks?|techniques?|directions?|stances?|weapons?|counting|"
                        r"general|practice|body|terms?)\s+", "", romaji, flags=re.I).strip()
        if not _ROMAJI.match(romaji) or len(romaji.split()) > 5 or not rest:
            continue
        km = re.match(r"\s*([^():：]*?)\s*(?:（|\()([^）)]*)(?:）|\))\s*[:：]\s*(.*)$", rest)
        if km:
            kanji, kana, english = km.group(1), km.group(2), km.group(3).strip()
        else:
            parts = re.split(r"[:：]", rest, 1)
            kanji, kana, english = (parts[0], "", parts[1].strip()) if len(parts) > 1 else (rest, "", "")
        # keep only the leading run of real CJK as the kanji (drop commentary/latin)
        km2 = re.match(r"[\s　]*([぀-ヿ㐀-鿿々]+(?:[\s　][぀-ヿ㐀-鿿々]+)*)", kanji)
        kanji = (km2.group(1).replace(" ", "").replace("　", "") if km2 else "")
        kana = re.sub(r"\[.*", "", kana).replace(" ", "").replace("　", "")  # drop bracketed notes
        kana = kana if re.fullmatch(r"[぀-ヿ]+", kana or "") else ""
        terms.append({"romaji": romaji, "kanji": [kanji] if kanji else [],
                      "kana": [kana] if kana else [],
                      "english": (english or None), "category": cur, "source": "aikidude"})
    return terms


_ROMAJI = re.compile(r"^[A-Za-z][A-Za-z'./()\- ]{1,34}$")


def parse_pdf(fn: str) -> list[dict]:
    """Conservative two-column parse: keep clean 'Romaji   English' pairs, drop prose."""
    txt = subprocess.run(["pdftotext", "-layout", str(RAW / fn), "-"],
                         capture_output=True, text=True).stdout
    terms, cur = [], None
    for line in txt.splitlines():
        # each physical line may hold two columns; split on runs of 2+ spaces
        cells = [c.strip() for c in re.split(r"\s{2,}", line.strip()) if c.strip()]
        # pair cells as (term, def): [t1, d1, t2, d2, ...]
        i = 0
        while i + 1 < len(cells):
            term, defn = cells[i], cells[i + 1]
            if (cat := cat_from_header(term)):
                cur = cat
            if _ROMAJI.match(term) and len(term.split()) <= 4 and re.search(r"[A-Za-z]", defn) and len(defn) > 3:
                term = re.sub(r"^\d+[.)]\s*", "", term).strip()   # drop "1. Ikkyo" numbering
                terms.append({"romaji": term, "kanji": [], "kana": [], "english": defn,
                              "category": cur, "source": fn.split(".")[0]})
            i += 2
    return terms


def merge(*lists: list[dict]) -> list[dict]:
    by: dict[str, dict] = {}
    for terms in lists:                       # order matters: curated first sets category
        for t in terms:
            sl = slugify(t["romaji"])
            if not sl:
                continue
            e = by.setdefault(sl, {"id": f"term:{sl}", "slug": sl, "romaji": t["romaji"],
                                   "kanji": [], "kana": [], "english": None, "category": None,
                                   "sources": [], "status": "provisional", "retrieved": TODAY})
            for k in t.get("kanji", []):
                if k and k not in e["kanji"]:
                    e["kanji"].append(k)
            for k in t.get("kana", []):
                if k and k not in e["kana"]:
                    e["kana"].append(k)
            if t.get("english") and not e["english"]:
                e["english"] = t["english"]
            if t.get("category") and not e["category"]:
                e["category"] = t["category"]
            if t["source"] not in e["sources"]:
                e["sources"].append(t["source"])
    return sorted(by.values(), key=lambda x: x["slug"])


def main() -> int:
    terms = merge(curated_core(), parse_aikidude(),
                  parse_pdf("greenwood.pdf"), parse_pdf("mcgill.pdf"), parse_pdf("redlands.pdf"))
    OUT.write_text(json.dumps(terms, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with_kanji = sum(1 for t in terms if t["kanji"])
    with_eng = sum(1 for t in terms if t["english"])
    print(f"wrote {len(terms)} terms -> {OUT}")
    print(f"  with kanji: {with_kanji} | with english: {with_eng}")
    from collections import Counter
    print("  by category:", dict(Counter(t["category"] for t in terms)))
    print("  by source:", dict(Counter(s for t in terms for s in t["sources"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
