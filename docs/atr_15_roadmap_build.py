#!/usr/bin/env python3
"""Render docs/atr_15_roadmap_graph.svg from atr_15_roadmap_graph.dot plus a
status legend, composed vertically (roadmap on top, legend centered below --
like a normal chart). Graphviz is rendered via kroki.io, so no local graphviz is
needed. Stdlib only.

Regenerate on demand:  python docs/atr_15_roadmap_build.py
"""

import base64
import re
import urllib.request
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
KROKI = "https://kroki.io/graphviz/svg/"
LEGEND = ('digraph L { rankdir=LR; nodesep=0.25; '
          'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=12]; '
          'd [label="done", fillcolor="#cfe8cf", color="#2e7d32"]; '
          'a [label="active", fillcolor="#fff3c4", color="#b8860b"]; '
          'n [label="next", fillcolor="#cfe0f5", color="#1565c0"]; '
          'f [label="future", fillcolor="#eeeeee", color="#999999"]; '
          'd->a->n->f [style=invis]; }')


def render_svg(dot: str) -> str:
    enc = base64.urlsafe_b64encode(zlib.compress(dot.encode(), 9)).decode()
    req = urllib.request.Request(KROKI + enc, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8")


def dims(svg: str) -> tuple[float, float]:
    w = float(re.search(r'<svg[^>]*\bwidth="([\d.]+)pt"', svg).group(1))
    h = float(re.search(r'<svg[^>]*\bheight="([\d.]+)pt"', svg).group(1))
    return w, h


def nest(svg: str, x: float, y: float, w: float, h: float) -> str:
    """Extract the inner <svg>...</svg> and position it as a nested svg (unitless)."""
    m = re.search(r"(<svg\b[^>]*>)(.*)(</svg>)", svg, re.S)
    open_tag = m.group(1)
    open_tag = re.sub(r'\swidth="[^"]*"', f' width="{w:.1f}"', open_tag, count=1)
    open_tag = re.sub(r'\sheight="[^"]*"', f' height="{h:.1f}"', open_tag, count=1)
    open_tag = re.sub(r"<svg\b", f'<svg x="{x:.1f}" y="{y:.1f}"', open_tag, count=1)
    return open_tag + m.group(2) + m.group(3)


def main() -> None:
    road = render_svg((HERE / "atr_15_roadmap_graph.dot").read_text())
    leg = render_svg(LEGEND)
    rw, rh = dims(road)
    lw, lh = dims(leg)
    gap = 24.0
    W, H = max(rw, lw), rh + gap + lh
    out = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{W:.0f}pt" height="{H:.0f}pt" viewBox="0 0 {W:.0f} {H:.0f}">\n'
        '<rect width="100%" height="100%" fill="white"/>\n'
        + nest(road, (W - rw) / 2, 0, rw, rh) + "\n"
        + nest(leg, (W - lw) / 2, rh + gap, lw, lh) + "\n</svg>\n"
    )
    (HERE / "atr_15_roadmap_graph.svg").write_text(out, encoding="utf-8")
    print(f"wrote atr_15_roadmap_graph.svg  ({W:.0f}x{H:.0f})")


if __name__ == "__main__":
    main()
