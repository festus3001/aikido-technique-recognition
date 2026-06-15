"""Format conversion for lay-readable outputs: markdown -> docx, SVG -> PNG.

Uses standard binaries (pandoc, rsvg-convert). PNGs get a small footer strip with
the rev + date stamped on, so the image file itself carries its version. Markdown
image links to .svg are rewritten to .png so the docx embeds a Word-friendly raster
rather than an SVG.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

_SVG_LINK = re.compile(r"(\]\()([^)]+?)\.svg(\))")


def md_to_docx(md_path: Path, out_path: Path, resource_dir: Path) -> None:
    """Convert markdown to docx, rewriting .svg image links to .png so Word shows them."""
    text = _SVG_LINK.sub(r"\1\2.png\3", md_path.read_text(encoding="utf-8"))
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tf:
        tf.write(text)
        tmp = Path(tf.name)
    try:
        subprocess.run(
            ["pandoc", str(tmp), "-o", str(out_path),
             "--resource-path", f"{resource_dir}:{md_path.parent}", "--standalone"],
            check=True, capture_output=True, text=True)
    finally:
        tmp.unlink(missing_ok=True)


def svg_to_png(svg_path: Path, out_path: Path, zoom: float = 2.0) -> None:
    if shutil.which("rsvg-convert"):
        subprocess.run(["rsvg-convert", "-z", str(zoom), "--background-color", "white",
                        "-o", str(out_path), str(svg_path)], check=True, capture_output=True)
    elif _has_cairosvg():
        import cairosvg
        cairosvg.svg2png(url=str(svg_path), write_to=str(out_path), scale=zoom, background_color="white")
    else:  # macOS fallback
        subprocess.run(["qlmanage", "-t", "-s", "2000", "-o", str(out_path.parent), str(svg_path)],
                       check=True, capture_output=True)
        thumb = out_path.parent / (svg_path.name + ".png")
        if thumb.exists():
            thumb.replace(out_path)


def _has_cairosvg() -> bool:
    import importlib.util
    return importlib.util.find_spec("cairosvg") is not None


def stamp_png_footer(png_path: Path, footer: str) -> None:
    """Add a white strip with the rev/date footer to the bottom of a PNG."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return
    img = Image.open(png_path).convert("RGB")
    strip = 34
    canvas = Image.new("RGB", (img.width, img.height + strip), "white")
    canvas.paste(img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
    draw.text((14, img.height + 8), footer, fill="#555555", font=font)
    canvas.save(png_path)
