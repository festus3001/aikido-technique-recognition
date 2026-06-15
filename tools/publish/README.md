# publish

Documentation build for the stakeholder Google Drive. Distills the repo docs into
lay-readable, click-to-open formats and stamps a date + revision on sources and
outputs.

## What it does
- `docs/*.md`  -> `.docx` (pandoc), with `.svg` image links rewritten to `.png` so Word shows them
- `docs/*.svg` -> `.png` (rsvg-convert), with a footer strip carrying rev + date
- writes everything to `dist/google-drive/` (gitignored) plus an `INDEX.md`
- stamps each source markdown footer `_ATR · <name> · rev <N> · <date> · <status>_`

Revision numbers live in `docs/revisions.json`, keyed by file with a content hash:
**a rev only bumps when the content actually changes** (footer edits do not count).
A brand-new doc keeps its existing footer date for rev 1; later changes stamp the
build date.

## Setup
System: `brew install pandoc librsvg`. Python env (PIL for the PNG footer):
```
conda run -n atr-ingest pip install -e tools/publish
```

## Run
```
conda run -n atr-ingest atr-publish                # build into dist/google-drive
conda run -n atr-ingest atr-publish --status final # mark outputs final
conda run -n atr-ingest atr-publish --date 2026-07-01
```
Then copy `dist/google-drive/` up to the shared Drive. Outputs are build artifacts
(not committed); the markdown, `revisions.json`, and this tool are the source of truth.

## Notes
- docx and png are regenerable, so `dist/` and `*.docx` are gitignored; the old
  committed `docs/*.docx` were removed in favor of this build.
- Drive sync itself is manual for now (copy the folder up); an API sync could be
  added later.
