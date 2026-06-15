# ingest

Book-ingestion pipeline: turns scanned, bilingual aikido PDFs into a structured
technique taxonomy and a set of tagged keyframe stills. The pivot of
docs/atr_09_book_ingestion from "TIFF masters -> OCR" to the reality on disk
(150 ppi scanned-image PDFs). Feeds both the project taxonomy (roadmap Phase 1)
and the AML motif lexicon (atr_14, P2).

## What it produces
- `data/taxonomy/techniques.json` -- one record per technique caption: bilingual
  name, surface slots (technique / attack / direction / form), step count,
  source (volume/page), provenance. Provisional, teacher-ratifiable.
- `data/taxonomy/keyframes.json` + `resources/books/processed/<vol>/<tech>/step_NN.png`
  -- each instructional photo saved as a tagged still: technique (romaji + native),
  step index, attack, source (volume/page/bbox), `granularity` (photo|row),
  `role: book-keyframe`, and `pose`/`embedding` left null. These are ground-truth
  keyframes for later video analysis: match a video frame to a book still to tag
  the technique position it shows.

## Pipeline
`render (pdftoppm) -> OCR (tesseract jpn+eng, pytesseract) -> filter to technique
captions (aikido lexicon) -> parse caption into slots -> segment photos
(projection rows, intra-row split when gutters exist) -> link caption to ordered
photos (adaptation layer) -> save keyframes + emit records (idempotent by id).`

## Setup
System prerequisites (Homebrew): `tesseract` and `poppler`. Japanese OCR data:
```
TD="$(brew --prefix)/share/tessdata"
for L in jpn jpn_vert; do
  curl -fsSL -o "$TD/$L.traineddata" \
    "https://github.com/tesseract-ocr/tessdata_best/raw/main/$L.traineddata"; done
```
Python env:
```
conda env create -f tools/ingest/environment.yml
conda run -n atr-ingest pip install -e tools/ingest
```

## Run
```
conda run -n atr-ingest atr-ingest --vol vol1 --pages 55-95   # a slice
conda run -n atr-ingest atr-ingest --all                      # every volume (long: 787 pages)
```
Flags: `--vol vol1..vol5` or `--all`, `--pages 55-95|60|12,40`, `--dpi 300`,
`--lang jpn+eng`, `--taxonomy`, `--processed`, `--retrieved`. Idempotent: re-runs
merge by deterministic id.

## Known limits (v1)
- Per-photo cell splitting works when rows have white gutters (~80% of cells on
  the slice); abutting framed photos fall back to a whole-row keyframe
  (`granularity: row`). Improving this (frame-edge detection or using the printed
  step numbers as a split guide) is the next step.
- `name_native` (kanji) is captured only when the OCR places it on/above the
  caption line; linking JP and romaji names reliably needs more work.
- OCR carries scan artifacts (macrons, dashes); slot matching is tolerant, but
  technique/attack slots should be teacher-ratified before they are treated as
  fact. Everything is emitted `status: provisional`.
