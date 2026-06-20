"""Store + merge logic, run against a temp taxonomy so the real data is untouched."""

import json

import pytest

from atr_contributor import store as store_mod
from atr_contributor.store import Store


@pytest.fixture
def taxo(tmp_path, monkeypatch):
    techs = [
        {"id": "tech:a", "name_romaji": "X", "slots": {"attack": "tsuki"}, "raw_caption": "(1) X",
         "step_count": 2, "source": {"book": "b", "pdf_page": 1}, "status": "provisional"},
        {"id": "tech:b", "name_romaji": "Y", "slots": {}, "raw_caption": "(2) Y",
         "step_count": 1, "source": {"book": "b", "pdf_page": 2}, "status": "provisional"},
    ]
    kfs = [
        {"id": "kf:a1", "technique": "tech:a", "step_index": 2, "image": "resources/books/processed/b/a/step_02.png"},
        {"id": "kf:a0", "technique": "tech:a", "step_index": 1, "image": "resources/books/processed/b/a/step_01.png"},
    ]
    (tmp_path / "techniques.json").write_text(json.dumps(techs))
    (tmp_path / "keyframes.json").write_text(json.dumps(kfs))
    monkeypatch.setattr(store_mod, "TAXO", tmp_path)
    monkeypatch.setattr(store_mod, "TECHNIQUES", tmp_path / "techniques.json")
    monkeypatch.setattr(store_mod, "KEYFRAMES", tmp_path / "keyframes.json")
    monkeypatch.setattr(store_mod, "REVIEWS", tmp_path / "reviews.json")
    return tmp_path


def test_keyframes_sorted_and_detail(taxo):
    s = Store("person:t", "T")
    d = s.detail("tech:a")
    assert [k["image"].split("/")[-1] for k in d["keyframes"]] == ["step_01.png", "step_02.png"]
    assert d["keyframes"][0]["img"] == "/img/b/a/step_01.png"
    assert d["review"] is None


def test_save_is_upsert_and_persists(taxo):
    s = Store("person:t", "T")
    s.save("tech:a", {"verdict": "corrected", "name_romaji": "tsuki kotegaeshi",
                      "slots": {"attack": "tsuki", "technique": "kotegaeshi", "direction": "ura", "form": ["tachiwaza"]},
                      "note": "soft kuzushi"})
    s.save("tech:a", {"verdict": "confirmed", "name_romaji": "tsuki kotegaeshi omote",
                      "slots": {"technique": "kotegaeshi", "direction": "omote"}})
    saved = json.loads((taxo / "reviews.json").read_text())
    assert len(saved) == 1  # upsert, not append
    assert saved[0]["verdict"] == "confirmed"
    assert saved[0]["slots"]["direction"] == "omote"
    assert saved[0]["id"] == "review:tech:a:person:t"

    fresh = Store("person:t", "T")  # reload from disk
    assert fresh.review_for("tech:a")["name_romaji"] == "tsuki kotegaeshi omote"
    assert fresh.progress()["reviewed"] == 1


def test_keyframe_edits_persist_and_drive_detail(taxo):
    s = Store("person:t", "T")
    # reorder + drop one + caption
    s.save("tech:a", {"verdict": "corrected", "keyframes": [
        {"image": "resources/books/processed/b/a/step_02.png", "caption": "first now"},
    ]})
    fresh = Store("person:t", "T")
    d = fresh.detail("tech:a")
    assert len(d["keyframes"]) == 1
    assert d["keyframes"][0]["caption"] == "first now"
    assert d["keyframes"][0]["img"] == "/img/b/a/step_02.png"  # effective seq = the review's


def test_keyframes_null_keeps_original(taxo):
    s = Store("person:t", "T")
    s.save("tech:a", {"verdict": "confirmed", "keyframes": None})
    d = Store("person:t", "T").detail("tech:a")
    assert len(d["keyframes"]) == 2  # provisional sequence


def test_reviewers_are_isolated(taxo):
    Store("person:t", "T").save("tech:a", {"verdict": "confirmed"})
    other = Store("person:u", "U")
    assert other.review_for("tech:a") is None
    assert other.progress()["reviewed"] == 0


def test_next_unreviewed_wraps(taxo):
    s = Store("person:t", "T")
    assert s.next_unreviewed() == "tech:a"
    s.save("tech:a", {"verdict": "confirmed"})
    assert s.next_unreviewed("tech:a") == "tech:b"
    s.save("tech:b", {"verdict": "skip"})
    assert s.next_unreviewed() is None


def test_merge_projects_reviewed_truth(taxo, monkeypatch):
    from atr_contributor import merge as merge_mod
    monkeypatch.setattr(merge_mod, "TECHNIQUES", taxo / "techniques.json")
    monkeypatch.setattr(merge_mod, "REVIEWS", taxo / "reviews.json")
    Store("person:t", "T").save("tech:a", {"verdict": "corrected", "name_romaji": "fixed",
                                           "slots": {"technique": "kotegaeshi", "direction": "ura"},
                                           "keyframes": [{"image": "resources/books/processed/b/a/step_01.png", "caption": "1"}]})
    out, counts = merge_mod.project()
    by_id = {t["id"]: t for t in out}
    assert by_id["tech:a"]["status"] == "reviewed"
    assert by_id["tech:a"]["name_romaji"] == "fixed"
    assert by_id["tech:a"]["slots"]["technique"] == "kotegaeshi"
    assert by_id["tech:a"]["slots"]["attack"] == "tsuki"  # original preserved
    assert by_id["tech:a"]["keyframes_reviewed"][0]["caption"] == "1"
    assert by_id["tech:b"]["status"] == "provisional"     # untouched
    assert counts["corrected"] == 1 and counts["unreviewed"] == 1
