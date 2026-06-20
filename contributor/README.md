# contributor

The teacher review loop (roadmap C4): the first real contribution loop, on text. A
teacher walks the ingested techniques, sees the book's step photos, and confirms or
corrects the name + compositional slots (attack / technique / direction / form), fixes
the image sequence, and adds a free-text note for the deep layer -- what the technique is
that the name does not carry.

Reviews never overwrite the provisional corpus. They land in `data/taxonomy/reviews.json`
as dated events keyed to the reviewing teacher (`person:<slug>`), the same provenance
stance used across the project. Re-reviewing a technique updates that teacher's record in
place.

## Run (you driving, locally)
One command -- it creates the env if missing, installs, starts the server, and opens the
browser:
```
contributor/review.sh --reviewer person:morihiro-saito-lineage-teacher --reviewer-name "Sensei Name"
```
Any flags are forwarded to `atr-review` (`--port`, `--host`, ...). Set `REVIEW_NO_OPEN=1`
to skip opening the browser. The long way, by hand:
```
conda env create -f contributor/environment.yml   # first time -> env atr-contributor
conda run -n atr-contributor pip install -e contributor
conda run -n atr-contributor atr-review --reviewer person:slug --reviewer-name "Name"
```
Either way, the tool is at http://127.0.0.1:8000/.

## What the teacher does per technique
- **Image sequence** -- the book's step photos. Reorder (`←`/`→`), delete (`×`), caption
  each frame, or **+ Add image** to pull in another photo from the same book (the ingester
  often splits or mislabels a sequence; this is the manual fix).
- **Name** -- romaji and Japanese are separate fields. OCR usually dumped Japanese into the
  romaji slot, so the tool routes that text into the Japanese box and leaves romaji blank
  for you to type; the **⇄** button swaps the two if they came in reversed.
- **Slots** -- attack / technique / direction / form, with autocomplete suggestions.
- **Note** -- the qualitative layer, in the teacher's words.
- Then a verdict: **Confirm as correct**, **Save correction**, **Skip**, or **Not a
  technique** (OCR noise / a section header / a weapons form mis-ingested). Each saves and
  jumps to the next unreviewed technique. Progress and resume are automatic, keyed to the
  teacher's slug so two teachers don't collide.

## Downstream
```
conda run -n atr-contributor atr-review-merge
```
Projects the reviews onto the corpus into `data/taxonomy/techniques_reviewed.json`: each
technique carries the teacher-approved name/slots where reviewed, the corrected keyframe
sequence if edited, and a `review` block (who / when / verdict / note). This is the
teacher-authorized view that the motif lexicon (D3), the first labeled dataset (F1), and
the parse model / evaluation set (F2, F4) should train and evaluate against. The
provisional `techniques.json` is never modified; `techniques_reviewed.json` is a
regenerable build artifact (gitignored).

## Layout
- `src/atr_contributor/store.py` -- corpus + review store (atomic upsert by teacher)
- `src/atr_contributor/app.py` -- FastAPI: queue / technique / image / review endpoints
- `src/atr_contributor/web/index.html` -- the one-page review UI (vanilla, no build step)
- `src/atr_contributor/merge.py` -- `atr-review-merge`, the reviewed projection
- `schema/review.schema.json` -- the review record contract
- `review.sh` -- the one-command launcher
- `app/` -- separate forward-looking stub for the future model-serving API (parse /
  contribution / clip routes); not part of this loop.
