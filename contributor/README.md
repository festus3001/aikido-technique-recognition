# contributor

The teacher review tool (roadmap C4) -- now **page-centric**: a wide split view that shows
the raw scanned page beside the parsed sequences, lets you re-parse a page live, and feeds
corrections back into the ingestion. Every correction -- a page region merge, a forced
caption, a volume section boundary, a new vocabulary term, a technique's name/slots/verdict --
is the same object: a **Refinement** (schema/refinement.py), authored, scoped, and resolved
by a cascade. Code defaults are the base; Refinements layer on top; the resolver yields the
effective interpretation, so the page interpretation refines further every pass.

## Run (you driving, locally)
```
contributor/review.sh --reviewer person:slug --reviewer-name "Sensei Name"
```
One command: creates the env if missing, installs the three editable packages
(`schema`, `tools/ingest`, `contributor`), starts the server, opens the browser.
Set `REVIEW_NO_OPEN=1` to skip the browser. System prerequisites are the same as the
ingest pipeline: **poppler** (`pdftoppm`) and **tesseract** + the `jpn`/`jpn_vert` traineddata.

## The page view
- Pick a **volume**; page **Prev/Next** (or jump to the next page with content).
- **Left**: the raw scanned page with a bbox overlay of the assigned photos (numbered
  `sequence.step`), hover-linked to the cards on the right.
- **Right**: the page's sequence cards. Each is the per-technique editor -- the keyframe
  sequence (reorder / delete / caption / add), name (romaji + Japanese, with auto-routing and a
  swap), attack/technique/direction/form slots, a deep-layer note, and a verdict
  (Confirm / Save correction / Skip / Not a technique). Saving writes technique-scope
  Refinements authored by the reviewer.

## Re-parse and commit (fixing the interpretation)
- **Re-parse this page** runs the ingestion live and shows a non-destructive **preview**: the
  overlay switches to the detected regions (click to select), and **Merge / Drop / Order** plus
  the **force-caption** control build page/sequence Refinements that re-parse on the spot. Iterate
  until the sequences are right.
- **Commit page** writes the result to the corpus (replacing that page's records, sorted to match
  a full re-ingest so a no-op commit is content-idempotent) and persists the overrides, so a later
  `atr-ingest --book <vol>` reproduces them.

## Teach the parser (the "▸ refinements" drawer)
- **Volume** -- edit the section map (page ranges -> context/kind/weapon/form) for the book.
- **Process** -- add a vocabulary term (slot + canonical + variants + kanji); re-parse to apply,
  and it teaches every book.
- **Refinements** -- the history for this book: each correction with author / date / status, with
  confirm and delete. This is the auditable record of progressive refinement.

## Downstream
```
conda run -n atr-contributor atr-review-merge
```
Resolves the technique-scope Refinements onto the corpus into `data/taxonomy/
techniques_reviewed.json` -- the teacher-authorized view for D3 / F1 / F2 / F4. The provisional
`techniques.json` is never mutated by review; corrections live in `data/refinements.json`.

## Layout
- `src/atr_contributor/store.py` -- corpus reader + RefinementStore-backed review/commit
- `src/atr_contributor/app.py` -- FastAPI: page / page-image / reparse / commit / refinement CRUD
- `src/atr_contributor/web/index.html` -- the one-page split UI (vanilla, no build step)
- `src/atr_contributor/merge.py` -- `atr-review-merge`
- `review.sh` -- the launcher
- The Refinement primitive itself lives in `schema/` (atr-schema), shared with ingestion.
- `app/` -- separate forward-looking stub for the future model-serving API; not this loop.
