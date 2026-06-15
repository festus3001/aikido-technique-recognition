"""Adaptation layer: associate a page's technique caption(s) with its photos and
order the photos into the step sequence.

Common case: one caption + N photos on a page or spread -> the technique gets all
N photos as steps 1..N in reading order. When a page carries more than one
caption, each photo is assigned to the vertically nearest caption, then ordered
within its group. This is where 'technique name -> images -> sequence' is formed.
"""

from __future__ import annotations

from .captions import Caption
from .photos import Region, order_reading


def link_page(captions: list[tuple[Caption, int]], boxes: list[Region]) -> list[tuple[Caption, list[Region]]]:
    """captions: list of (Caption, caption_top_y). boxes: photo boxes (reading order).
    Returns [(caption, ordered_boxes)]."""
    if not captions:
        return []
    if len(captions) == 1:
        return [(captions[0][0], boxes)]

    caps = sorted(captions, key=lambda c: c[1])
    groups: list[list[Box]] = [[] for _ in caps]
    for b in boxes:
        center_y = b[1] + b[3] / 2
        nearest = min(range(len(caps)), key=lambda j: abs(center_y - caps[j][1]))
        groups[nearest].append(b)
    return [(caps[i][0], order_reading(groups[i])) for i in range(len(caps))]
