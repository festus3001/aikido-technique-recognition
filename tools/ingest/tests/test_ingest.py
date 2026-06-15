"""Offline tests for the deterministic ingest stages (no OCR / no PDF)."""

import numpy as np

from atr_ingest import captions, keyframes, photos
from atr_ingest.store import Store
from atr_ingest.util import slugify


# -- caption parsing & lexicon ---------------------------------------------

def test_parse_caption_kokyu_nage():
    cap = captions.parse_caption("Kokyu Nage (Tachi dori) (Tsuki)", native="呼吸投げ")
    assert cap.name_romaji == "Kokyu Nage"
    assert cap.qualifiers == ["Tachi dori", "Tsuki"]
    assert cap.slots["technique"] == "kokyu-nage"
    assert cap.slots["attack"] == "tsuki"
    assert "tachi-dori" in cap.slots["form"]
    assert cap.name_native == "呼吸投げ"
    assert cap.slug() == "kokyu-nage-tachi-dori-tsuki"


def test_classify_kanji_names():
    # Vol.2 pins are named in kanji; the matcher must read them
    assert captions.classify("第一教")["technique"] == ["ikkyo"]
    assert captions.classify("第五教")["technique"] == ["gokyo"]
    c = captions.classify("正面打ち四方投げ（表）")
    assert c["attack"] == ["shomen-uchi"] and c["technique"] == ["shiho-nage"] and c["direction"] == ["omote"]


def test_kanji_caption_and_slug():
    cap = captions.parse_caption("正面打ち第一教（表）")
    assert cap.slots["technique"] == "ikkyo" and cap.slots["attack"] == "shomen-uchi"
    assert cap.slug() == "shomen-uchi-ikkyo-omote"   # slug built from slots, not empty
    assert captions.is_caption("第二教")              # a kanji-only title is a caption


def test_merge_bilingual_same_technique():
    # romaji + kanji titles for the same technique on one page -> one record,
    # keeping the romaji name, the kanji as native, and the richer (omote) slot.
    romaji = captions.parse_caption("Shomen Uchi Shi-ho-nage")          # no direction
    kanji = captions.parse_caption("正面打ち四方投げ表技", native="正面打ち四方投げ")  # omote
    out = captions.merge_bilingual([(romaji, 100), (kanji, 400)])
    assert len(out) == 1
    m = out[0][0]
    assert m.name_romaji == "Shomen Uchi Shi-ho-nage"
    assert m.name_native and "四方投げ" in m.name_native
    assert m.slots["technique"] == "shiho-nage" and m.slots["direction"] == "omote"


def test_merge_bilingual_keeps_distinct():
    # omote and ura are different techniques -> must NOT merge
    a = captions.parse_caption("Shomen Uchi Shi-ho-Nage—Omote waza")
    b = captions.parse_caption("正面打ち四方投げ裏技")
    out = captions.merge_bilingual([(a, 100), (b, 400)])
    assert len(out) == 2
    # two distinct romaji suburi also stay separate (both ascii)
    c = captions.parse_caption("Choku tsuki")
    d = captions.parse_caption("Kaeshi Tsuki")
    assert len(captions.merge_bilingual([(c, 1), (d, 2)])) == 2


def test_japanese_prose_rejected():
    # explanatory Japanese sentence mentioning the pins must NOT be a caption
    assert not captions.is_caption("「第一教」から「第五教」の技は次の巻にて説明いたします")


def test_parse_caption_inline_attack_and_direction():
    cap = captions.parse_caption("Katate-dori Shiho-nage Omote")
    assert cap.slots["technique"] == "shiho-nage"
    assert cap.slots["attack"] == "katate-dori"
    assert cap.slots["direction"] == "omote"


def test_classify_longest_match_wins():
    # ushiro-ryote-dori must not be mis-read as ryote-dori
    c = captions.classify("Ushiro Ryote-dori Kotegaeshi")
    assert c["attack"] == ["ushiro-ryote-dori"]
    assert c["technique"] == ["kote-gaeshi"]


def test_is_caption_filters_noise():
    assert captions.is_caption("Ikkyo (Shomen-uchi) (Omote)")
    assert not captions.is_caption("tee")
    assert not captions.is_caption("Bae.")
    assert not captions.is_caption("— 58 —")


def test_is_caption_rejects_prose_and_crossrefs():
    # real titles survive
    assert captions.is_caption("Shomen Uchi Kote Gaeshi")
    assert captions.is_caption("Kokyu Nage (Tachi dori) (Tsuki)")
    assert captions.is_caption("Shomen Uchi Shi-ho-Nage—Omote waza")
    # prose and cross-references are rejected
    assert not captions.is_caption("henko, and kokyu dosa consistently.")
    assert not captions.is_caption("page 45). This exercise is yonkyo.")
    assert not captions.is_caption("receive your opponent's Ki because you have in")
    assert not captions.is_caption("(Refer to ushiro tsuki)")
    assert not captions.is_caption("This is one of the kokyu, or breath, techniques.")


def test_slugify_folds_macron():
    assert slugify("Kokyū Nage") == "kokyu-nage"


# -- photo segmentation & ordering -----------------------------------------

def test_order_reading_row_major():
    boxes = [(400, 10, 100, 80), (10, 12, 100, 80), (10, 300, 100, 80)]
    ordered = photos.order_reading(boxes)
    assert ordered[0][0] == 10 and ordered[0][1] == 12   # top-left first
    assert ordered[1][0] == 400                          # then top-right
    assert ordered[2][1] == 300                          # then second row


def test_detect_photo_regions_synthetic():
    img = np.full((1400, 1000, 3), 255, np.uint8)        # white page
    import cv2
    cv2.rectangle(img, (100, 100), (400, 350), (20, 20, 20), -1)   # photo 1 (top)
    cv2.rectangle(img, (100, 700), (400, 950), (20, 20, 20), -1)   # photo 2 (bottom)
    boxes = photos.detect_photo_regions(img)
    assert len(boxes) == 2
    assert boxes[0][1] < boxes[1][1]                     # reading order top-to-bottom


# -- keyframes & store -----------------------------------------------------

def test_build_records_and_keyframe_context(tmp_path):
    page = np.full((1400, 1000, 3), 128, np.uint8)
    cap = captions.parse_caption("Kote-gaeshi (Tsuki)", native="小手返し")
    boxes = [(100, 100, 200, 150), (350, 100, 200, 150), (100, 300, 200, 150)]
    vol = {"id": "vol1", "title": "Basic Techniques", "performer": "person:morihiro-saito",
           "performer_name": "Morihiro Saito", "era": {"start": "1973", "end": "1976",
           "confidence": "inferred", "note": "x"}, "lineage": "iwama"}
    tech, kfs = keyframes.build_records(vol, cap, boxes, page, 60, tmp_path, "2026-06-13",
                                        repo_root=tmp_path)
    assert tech["step_count"] == 3 and tech["slots"]["technique"] == "kote-gaeshi"
    assert len(kfs) == 3 and tech["keyframes"] == [k["id"] for k in kfs]
    kf = kfs[1]
    assert kf["step_index"] == 2 and kf["role"] == "book-keyframe"
    assert kf["pose"] is None and kf["embedding"] is None          # downstream hooks
    assert kf["attack"] == "tsuki" and kf["source"]["bbox"] == [350, 100, 200, 150]
    # observation provenance: performer (person:slug into data/map), era, medium
    for rec in (tech, kf):
        p = rec["provenance"]
        assert p["performer"] == "person:morihiro-saito" and p["medium"] == "book"
        assert p["recording"] == "vol1" and p["era"]["confidence"] == "inferred"
        assert p["lineage"] == "iwama"
    # the still was actually written
    assert (tmp_path / "vol1" / "p60-kote-gaeshi-tsuki" / "step_02.png").exists()


def test_store_idempotent(tmp_path):
    store = Store(tmp_path)
    rec = {"id": "tech:x", "name_romaji": "X"}
    store.upsert("techniques", rec)
    store.upsert("techniques", rec)
    assert store.count("techniques") == 1
