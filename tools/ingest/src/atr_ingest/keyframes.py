"""Save instructional photos as tagged keyframes, and build records.

Each photo is cropped from the page and written to
resources/books/processed/<volume>/<technique-slug>/step_NN.png, with a keyframe
record carrying its technique (romaji + native), step index, attack, and source
(volume / page / bbox). These are ground-truth stills for later video analysis:
a video frame can be matched to a book keyframe to tag the technique position it
shows. `pose` and `embedding` are left null as hooks for that downstream step.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .captions import Caption


def build_records(book: dict, caption: Caption, boxes: list[tuple[int, int, int, int]],
                  page_img: np.ndarray, pdf_page: int, processed_root: Path,
                  retrieved: str, repo_root: Path | None = None) -> tuple[dict, list[dict]]:
    """Crop and save each photo; return (technique_record, [keyframe_records])."""
    repo_root = repo_root or processed_root
    vol = book["id"]  # canonical book slug, used on the path and in ids
    slug = caption.slug()
    # observation provenance: who performed, when, from which recording. The
    # performer is a person:slug resolving into the lineage data map; era is the
    # source's era (a 1970s book vs a later video are distinct observations).
    provenance = {
        "performer": book.get("performer"),
        "performer_name": book.get("performer_name"),
        "era": book.get("era"),
        "medium": "book",
        "recording": book["id"],
        "lineage": book.get("lineage"),
    }
    tech_id = f"tech:{vol}-p{pdf_page}-{slug}"
    out_dir = processed_root / vol / f"p{pdf_page}-{slug}"
    out_dir.mkdir(parents=True, exist_ok=True)

    keyframes: list[dict] = []
    for i, box in enumerate(boxes, start=1):
        x, y, w, h = box[:4]
        granularity = box[4] if len(box) > 4 else "photo"
        crop = page_img[max(0, y):y + h, max(0, x):x + w]
        rel = out_dir / f"step_{i:02d}.png"
        cv2.imwrite(str(rel), crop)
        try:
            image_path = str(rel.resolve().relative_to(repo_root.resolve()))
        except ValueError:
            image_path = str(rel)
        kf_id = f"kf:{vol}-p{pdf_page}-{slug}-{i:02d}"
        keyframes.append({
            "id": kf_id,
            "technique": tech_id,
            "step_index": i,
            "step_count": len(boxes),
            "image": image_path,
            "name_romaji": caption.name_romaji,
            "name_native": caption.name_native,
            "attack": caption.slots.get("attack"),
            "source": {"book": vol, "title": book.get("full_title"), "pdf_page": pdf_page,
                       "bbox": [int(x), int(y), int(w), int(h)]},
            "provenance": provenance,
            "granularity": granularity,
            "role": "book-keyframe",
            "pose": None,
            "embedding": None,
            "status": "provisional",
            "retrieved": retrieved,
        })

    technique = {
        "id": tech_id,
        "name_romaji": caption.name_romaji,
        "name_native": caption.name_native,
        "qualifiers": caption.qualifiers,
        "slots": caption.slots,
        "step_count": len(boxes),
        "keyframes": [k["id"] for k in keyframes],
        "source": {"book": vol, "title": book.get("full_title"), "pdf_page": pdf_page},
        "provenance": provenance,
        "raw_caption": caption.raw,
        "confidence": "ocr",
        "status": "provisional",
        "retrieved": retrieved,
    }
    return technique, keyframes
