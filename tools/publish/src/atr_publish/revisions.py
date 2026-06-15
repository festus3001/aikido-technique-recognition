"""Date + revision-number management and footer stamping.

Each document carries a footer line:  _ATR · <name> · rev <N> · <YYYY-MM-DD> · <status>_
Revision numbers live in docs/revisions.json, keyed by asset filename, with the
content hash (excluding the footer) so a rev only bumps when the content actually
changes. Re-running the build re-stamps the footer to match the manifest; the
matching outputs (docx / png) inherit the same rev + date.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

FOOTER_RE = re.compile(r"(?m)^_ATR\b.*_\s*$")
NAME_RE = re.compile(r"_ATR · (.+?) · rev")
DATE_RE = re.compile(r"rev (?:\d+ · )?(\d{4}-\d{2}-\d{2})")


def content_hash(text: str) -> str:
    body = FOOTER_RE.sub("", text).strip()
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]


def existing_name(text: str) -> str | None:
    m = NAME_RE.search(text)
    return m.group(1).strip() if m else None


def existing_date(text: str) -> str | None:
    m = DATE_RE.search(text)
    return m.group(1) if m else None


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                    encoding="utf-8")


def bump(manifest: dict, key: str, text: str, date: str, first_date: str | None = None) -> tuple[int, str]:
    """Return (rev, date) for this asset, bumping rev iff content changed.
    A brand-new asset uses first_date (e.g. its existing footer date) if given."""
    h = content_hash(text)
    prev = manifest.get(key)
    if prev is None:
        rev, rdate = 1, (first_date or date)
    elif prev.get("hash") != h:
        rev, rdate = prev.get("rev", 0) + 1, date
    else:
        rev, rdate = prev["rev"], prev["date"]
    manifest[key] = {"rev": rev, "date": rdate, "hash": h}
    return rev, rdate


def bump_blob(manifest: dict, key: str, blob: bytes, date: str) -> tuple[int, str]:
    """Rev bump for a non-text asset (e.g. an SVG), hashed whole."""
    h = hashlib.sha256(blob).hexdigest()[:12]
    prev = manifest.get(key)
    if prev is None:
        rev, rdate = 1, date
    elif prev.get("hash") != h:
        rev, rdate = prev.get("rev", 0) + 1, date
    else:
        rev, rdate = prev["rev"], prev["date"]
    manifest[key] = {"rev": rev, "date": rdate, "hash": h}
    return rev, rdate


def stamp_footer(text: str, name: str, rev: int, date: str, status: str = "draft") -> str:
    footer = f"_ATR · {name} · rev {rev} · {date} · {status}_"
    if FOOTER_RE.search(text):
        return FOOTER_RE.sub(footer, text)
    return text.rstrip() + "\n\n---\n\n" + footer + "\n"
