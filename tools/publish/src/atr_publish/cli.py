"""Build stakeholder-facing docs into dist/ for the Google Drive upload.

  atr-publish                 # stamp rev+date, build docx + png into dist/google-drive
  atr-publish --status final  # mark the footer status

Markdown -> docx, SVG -> PNG. Each source doc and each output carries a date and
revision number; revisions bump only when content changed (docs/revisions.json).
"""

from __future__ import annotations

import argparse
from datetime import date as _date
from pathlib import Path

from . import convert, revisions

REPO_ROOT = Path(__file__).resolve().parents[4]
PKG_ROOT = Path(__file__).resolve().parents[2]  # tools/publish
DOCS = REPO_ROOT / "docs"
MANIFEST = DOCS / "revisions.json"
DEFAULT_OUT = REPO_ROOT / "dist" / "google-drive"
GDRIVE_DIR = PKG_ROOT / ".gdrive"


def display_name(text: str, path: Path) -> str:
    """Prefer the existing footer name; else derive from the filename."""
    return revisions.existing_name(text) or path.stem.split("_", 2)[-1].replace("_", " ")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="atr-publish", description="Build stakeholder docs (docx + png)")
    p.add_argument("--docs", type=Path, default=DOCS)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--date", default=_date.today().isoformat(), help="build date (YYYY-MM-DD)")
    p.add_argument("--status", default="draft", help="footer status, e.g. draft | final")
    p.add_argument("--push", action="store_true",
                   help="upload outputs to Google Drive as native Google Docs / images")
    p.add_argument("--folder-name", default="ATR documents",
                   help="Drive folder to upload into (created if absent); ignored if --folder-id given")
    p.add_argument("--folder-id", default=None,
                   help="upload into this exact Drive folder id (incl. a Shared Drive)")
    p.add_argument("--credentials", type=Path, default=GDRIVE_DIR / "credentials.json",
                   help="Google OAuth client file (Desktop type)")
    args = p.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    manifest = revisions.load_manifest(MANIFEST)
    outputs: list[tuple[str, int, str, str]] = []  # (asset, rev, date, output file)

    # 1. SVG -> PNG first, so the docx can embed the PNG.
    for svg in sorted(args.docs.glob("*.svg")):
        name = svg.stem.split("_", 2)[-1].replace("_", " ")
        rev, rdate = revisions.bump_blob(manifest, svg.name, svg.read_bytes(), args.date)
        png = args.out / f"{svg.stem}.png"
        convert.svg_to_png(svg, png)
        convert.stamp_png_footer(png, f"ATR · {name} · rev {rev} · {rdate} · {args.status}")
        outputs.append((svg.name, rev, rdate, png.name))

    # 2. Markdown: stamp rev+date into the source footer, then build docx.
    for md in sorted(args.docs.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        name = display_name(text, md)
        rev, rdate = revisions.bump(manifest, md.name, text, args.date,
                                    first_date=revisions.existing_date(text))
        stamped = revisions.stamp_footer(text, name, rev, rdate, args.status)
        if stamped != text:
            md.write_text(stamped, encoding="utf-8")
        docx = args.out / f"{md.stem}.docx"
        convert.md_to_docx(md, docx, resource_dir=args.out)
        outputs.append((md.name, rev, rdate, docx.name))

    revisions.save_manifest(MANIFEST, manifest)

    # 3. An index so the Drive folder is self-describing.
    lines = [f"# ATR documents (built {args.date})", "",
             "Stakeholder copies. Source of truth is the markdown in the repo; these are built by",
             "tools/publish (`atr-publish`). Each file carries its revision and date.", "",
             "| Source | Rev | Date | Output |", "|---|---|---|---|"]
    for asset, rev, rdate, outfile in sorted(outputs):
        lines.append(f"| {asset} | {rev} | {rdate} | {outfile} |")
    (args.out / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Built {len(outputs)} output(s) -> {args.out}")
    print(f"  docx: {sum(1 for o in outputs if o[3].endswith('.docx'))} | "
          f"png: {sum(1 for o in outputs if o[3].endswith('.png'))}")
    print(f"  revisions: {MANIFEST}")

    if args.push:
        from . import drive
        print(f"Pushing to Google Drive (folder: {args.folder_name!r}) ...")
        built = [args.out / o[3] for o in sorted(outputs)]
        link = drive.push(args.out, built, args.credentials,
                          GDRIVE_DIR / "token.json", args.folder_name, args.folder_id)
        print(f"Done. Open the folder: {link}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
