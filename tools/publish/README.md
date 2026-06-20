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

## Push to Google Drive (as native Google Docs)
`--push` uploads the build straight into a Drive folder, converting each docx to a
**native Google Doc** on the way in (PNGs upload as images). Nobody opens a .docx.
Re-pushing updates the same files in place (their links are stable), so it is safe to
run every build.

```
conda run -n atr-ingest atr-publish --push                          # into "ATR documents" in My Drive
conda run -n atr-ingest atr-publish --push --folder-name "ATR docs" # a different My Drive folder
conda run -n atr-ingest atr-publish --push --folder-id <FOLDER_ID>  # an exact folder, incl. a Shared Drive
conda run -n atr-ingest atr-publish --status final --push           # build + push in one go
```

`--folder-id` takes the id from a Drive folder URL
(`drive.google.com/drive/folders/<FOLDER_ID>`) and uploads straight into it, Shared
Drives included. Without it, the tool finds-or-creates `--folder-name` in My Drive.

One-time Google setup (about 5 minutes):
1. Go to https://console.cloud.google.com -> create a project (any name).
2. APIs & Services -> Library -> enable **Google Drive API**.
3. APIs & Services -> OAuth consent screen -> set the app to **Internal** (Workspace
   org). Internal apps need no test users and no Google verification, even for the
   full `drive` scope the tool uses.
4. APIs & Services -> Credentials -> Create credentials -> **OAuth client ID** ->
   application type **Desktop app** -> Download JSON.
5. Save that file as `tools/publish/.gdrive/credentials.json`.

The first `--push` opens a browser to approve; the token is cached at
`tools/publish/.gdrive/token.json`, so later pushes are non-interactive. The `.gdrive/`
folder (client secret + token) is gitignored and never committed.

Scope: `https://www.googleapis.com/auth/drive`. The full Drive scope is used so the
tool can target an existing folder by id, including a Shared Drive (the narrower
`drive.file` scope can only touch folders the tool itself created). It is an Internal
Workspace app, so this needs no Google verification.

## Notes
- docx and png are regenerable, so `dist/` and `*.docx` are gitignored; the old
  committed `docs/*.docx` were removed in favor of this build.
- Without `--push`, the build just lands in `dist/google-drive/` to copy up by hand.
