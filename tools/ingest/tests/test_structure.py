"""Structure-aware ingestion: section maps + weapon-caption handling (no OCR/PDF)."""

import numpy as np

from atr_ingest import captions, keyframes
from atr_ingest.structure import section_for


# -- section map ---------------------------------------------------------------

def test_vol1_section_lookup():
    # taijutsu body of Vol.1
    s = section_for("saito-traditional-aikido-vol1", 60)
    assert s.context == "taijutsu" and s.kind == "technique" and not s.is_weapon
    # the aiki-jo region (the 31-jo-kata / suburi the user flagged at ~p83)
    j = section_for("saito-traditional-aikido-vol1", 86)
    assert j.context == "aiki-jo" and j.weapon == "jo" and j.is_weapon
    assert j.form == "31-no-jo"
    # ken suburi up front (previously dropped entirely)
    k = section_for("saito-traditional-aikido-vol1", 30)
    assert k.context == "aiki-ken" and k.weapon == "ken"
    # front matter is skipped
    assert section_for("saito-traditional-aikido-vol1", 5).kind == "skip"


def test_unmapped_book_falls_back_to_taijutsu():
    s = section_for("some-other-book", 40)
    assert s.context == "taijutsu" and s.kind == "technique"


# -- weapon captions -----------------------------------------------------------

def test_section_header_is_not_a_caption():
    assert captions.is_section_header("[ 突き の 部 ]")
    assert not captions.is_weapon_caption("[ 突き の 部 ]")   # header sets context, emits nothing


def test_weapon_caption_detected_and_parsed():
    assert captions.is_weapon_caption("(1) 直 突き")
    cap = captions.parse_weapon_caption("(1) 直 突き")
    assert cap.qualifiers == ["1"]
    assert cap.name_native == "直突き"
    assert cap.slots["attack"] is None            # a jo thrust is NOT an attack
    assert captions.is_weapon_caption("素振り 一 (3)")


def test_weapon_record_has_no_attack_and_carries_context():
    sec = section_for("saito-traditional-aikido-vol1", 86)   # aiki-jo
    cap = captions.parse_weapon_caption("(1) 直 突き")
    img = np.zeros((400, 400, 3), dtype=np.uint8)
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        book = {"id": "saito-traditional-aikido-vol1", "full_title": "Vol.1",
                "performer": "person:morihiro-saito", "lineage": "iwama"}
        tech, kfs = keyframes.build_records(book, cap, [(10, 10, 100, 100)], img, 86,
                                            Path(d), "2026-06-20", repo_root=Path(d),
                                            section=sec, seq=1)
    assert tech["kind"] == "suburi" and tech["context"] == "aiki-jo" and tech["weapon"] == "jo"
    assert tech["form"] == "31-no-jo"
    assert tech["slots"]["attack"] is None
    assert kfs[0]["attack"] is None
    assert tech["id"].startswith("tech:saito-traditional-aikido-vol1-p86-")
