# glossary

Builds `data/taxonomy/glossary.json` -- the bilingual aikido **term base**. This is the
shared spine for two things: the parser's lexicon (the technique/attack/direction/form
vocabulary) and the coming local translator's domain RAG (kanji -> English term mappings,
injected so technical terms translate correctly and consistently). It is also, in itself,
a large chunk of the taxonomy the project was missing.

Every term is provisional and teacher-correctable, and records which source(s) it came from.

## Sources (seed)
- **atr-lexicon** -- the project's own curated lexicon (`tools/ingest .../captions.py`):
  verified romaji + kanji, by slot. The high-confidence core.
- **aikidude** -- https://aikidude.wordpress.com/aikido-glossary/ (categorized; kanji + kana +
  English). The main kanji-bearing breadth source.
- **greenwood / mcgill / redlands** -- downloadable dojo glossary PDFs (romaji + English,
  by section); breadth + English glosses, no kanji.
- candidate, not held: **"The Language of Aikido"** (Hacker, ISBN 978-0-692-90745-0) -- an
  authoritative JP/romaji/English reference to ingest later (see data/taxonomy/sources.json).

Raw downloads live under `resources/glossaries/raw/` (gitignored -- third-party material, not
redistributed). Re-fetch:
```
curl -fsSL -A Mozilla/5.0 -o resources/glossaries/raw/redlands.pdf  https://aikidoredlands.org/classes/aikido/glossary.pdf
curl -fsSL -A Mozilla/5.0 -o resources/glossaries/raw/greenwood.pdf https://greenwoodaikido.com/AikidoGlossary.pdf
curl -fsSL -A Mozilla/5.0 -o resources/glossaries/raw/mcgill.pdf    https://mcgillaikido.com/wp-content/uploads/2025/01/Aikido_glossary.pdf
curl -fsSL -A Mozilla/5.0 -o resources/glossaries/raw/aikidude.html https://aikidude.wordpress.com/aikido-glossary/
```

## Build
```
conda run -n atr-ingest python tools/glossary/build.py
```
Reads the raw sources + the curated lexicon, merges/dedupes by romaji slug, writes
`data/taxonomy/glossary.json`. Re-runnable; deterministic given the raw files.

## Term schema
```
{ "id":"term:<slug>", "slug", "romaji", "kanji":[...], "kana":[...], "english",
  "category": attack|technique|direction|form|weapon|count|practice|body|general|null,
  "sources":[...], "status":"provisional", "retrieved":"YYYY-MM-DD" }
```

## Notes / next
- Parsing public glossaries is best-effort: categories and English glosses on non-curated
  terms are provisional (the dojo PDFs are romaji-only; some categories are unknown/null).
- This term base feeds the local translator (Ollama + glossary RAG) and is grown/corrected
  by the teacher through the Refinement model.
