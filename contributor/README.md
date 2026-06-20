# contributor

The teacher ratification loop (roadmap C4): the first real contribution loop, on text.
A teacher walks the ingested techniques, sees the book's step photos, and confirms or
corrects the name + compositional slots (attack / technique / direction / form), plus a
free-text note for the deep layer -- what the technique is that the name does not carry.

Corrections never overwrite the provisional corpus. They land in
`data/taxonomy/ratifications.json` as dated events keyed to the ratifying teacher
(`person:<slug>`), the same provenance stance used across the project. Re-reviewing a
technique updates that teacher's record in place.

## Run (you driving, locally)
```
conda env create -f contributor/environment.yml   # first time -> env atr-contributor
conda run -n atr-contributor pip install -e contributor
conda run -n atr-contributor atr-ratify \
    --reviewer person:morihiro-saito-lineage-teacher \
    --reviewer-name "Sensei Name"
```
Open http://127.0.0.1:8000/. For each technique: the step photos are shown in order; the
fields are prefilled from the OCR parse. Fix the romaji/Japanese name and the slots, add a
note if you wish, then:

- **Confirm as correct** -- the parse was right
- **Save correction** -- the fields you left are the teacher's truth
- **Skip** -- come back later
- **Not a technique** -- OCR noise / not a real entry (rejected)

Each button saves and jumps to the next unreviewed technique. Progress and resume are
automatic (the reviewer key is the teacher's slug, so two teachers don't collide).

## Downstream
```
conda run -n atr-contributor atr-ratify-merge
```
Projects the ratifications onto the corpus into `data/taxonomy/techniques_ratified.json`:
each technique carries the teacher-approved name/slots where ratified, with a `ratification`
block (who / when / verdict / note). This is the teacher-authorized view that the motif
lexicon (D3), the first labeled dataset (F1), and the parse model / evaluation set (F2, F4)
should train and evaluate against. The provisional `techniques.json` is never modified;
`techniques_ratified.json` is a regenerable build artifact (gitignored).

## Layout
- `src/atr_contributor/store.py` -- corpus + ratification store (atomic upsert by teacher)
- `src/atr_contributor/app.py` -- FastAPI: queue / technique / image / ratify endpoints
- `src/atr_contributor/web/index.html` -- the one-page review UI (vanilla, no build step)
- `src/atr_contributor/merge.py` -- `atr-ratify-merge`, the ratified projection
- `schema/ratification.schema.json` -- the ratification record contract
- `app/` -- separate forward-looking stub for the future model-serving API (parse /
  contribution / clip routes); not part of this loop.
