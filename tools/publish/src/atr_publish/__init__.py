"""ATR documentation publish/build.

Distills the project docs into lay-readable, click-to-open formats for the
stakeholder Google Drive: markdown -> docx, SVG -> PNG, written to dist/ for easy
copy-up. Stamps a date + revision number on each source doc and its outputs;
revisions bump only when content changes (tracked in docs/revisions.json).
"""

__version__ = "0.1.0"
