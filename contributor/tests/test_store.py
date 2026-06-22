"""Store + merge logic on the Refinement model, against a temp corpus + refinements file."""

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
    monkeypatch.setattr(store_mod, "TECHNIQUES", tmp_path / "techniques.json")
    monkeypatch.setattr(store_mod, "KEYFRAMES", tmp_path / "keyframes.json")
    monkeypatch.setattr(store_mod, "REFINEMENTS", tmp_path / "refinements.json")
    return tmp_path


def test_detail_uses_original_sequence_when_unreviewed(taxo):
    s = Store("person:t", "T")
    d = s.detail("tech:a")
    assert [k["image"].split("/")[-1] for k in d["keyframes"]] == ["step_01.png", "step_02.png"]
    assert d["review"] is None


def test_save_writes_refinements_and_reconstructs_review(taxo):
    s = Store("person:t", "T")
    s.save("tech:a", {"verdict": "corrected", "name_romaji": "tsuki kotegaeshi",
                      "name_native": "突き小手返し",
                      "slots": {"attack": "tsuki", "technique": "kotegaeshi", "direction": "ura", "form": ["tachiwaza"]},
                      "note": "soft kuzushi"})
    refs = json.loads((taxo / "refinements.json").read_text())
    targets = {r["target"] for r in refs}
    assert {"verdict", "name", "parse.slots", "note"} <= targets
    assert all(r["scope"]["level"] == "technique" for r in refs)

    fresh = Store("person:t", "T").review_for("tech:a")
    assert fresh["verdict"] == "corrected"
    assert fresh["name_romaji"] == "tsuki kotegaeshi"
    assert fresh["slots"]["direction"] == "ura"
    assert fresh["note"] == "soft kuzushi"
    assert Store("person:t", "T").progress()["reviewed"] == 1


def test_keyframe_edits_persist_and_drive_detail(taxo):
    s = Store("person:t", "T")
    s.save("tech:a", {"verdict": "corrected", "keyframes": [
        {"image": "resources/books/processed/b/a/step_02.png", "caption": "first now"}]})
    d = Store("person:t", "T").detail("tech:a")
    assert len(d["keyframes"]) == 1
    assert d["keyframes"][0]["caption"] == "first now"
    assert d["keyframes"][0]["img"] == "/img/b/a/step_02.png"


def test_reviewers_are_isolated_by_author(taxo):
    Store("person:t", "T").save("tech:a", {"verdict": "confirmed"})
    other = Store("person:u", "U")
    assert other.review_for("tech:a") is None          # u has not reviewed it
    assert other.progress()["reviewed"] == 0
    other.save("tech:a", {"verdict": "rejected"})       # both authors' verdicts coexist
    refs = json.loads((taxo / "refinements.json").read_text())
    assert len([r for r in refs if r["target"] == "verdict"]) == 2


def test_next_unreviewed_wraps(taxo):
    s = Store("person:t", "T")
    assert s.next_unreviewed() == "tech:a"
    s.save("tech:a", {"verdict": "confirmed"})
    assert Store("person:t", "T").next_unreviewed("tech:a") == "tech:b"
    Store("person:t", "T").save("tech:b", {"verdict": "skip"})
    assert Store("person:t", "T").next_unreviewed() is None


def test_merge_projects_reviewed_truth(taxo, monkeypatch):
    from atr_contributor import merge as merge_mod
    monkeypatch.setattr(merge_mod, "TECHNIQUES", taxo / "techniques.json")
    monkeypatch.setattr(merge_mod, "REFINEMENTS", taxo / "refinements.json")
    Store("person:t", "T").save("tech:a", {"verdict": "corrected", "name_romaji": "fixed",
                                           "slots": {"technique": "kotegaeshi", "direction": "ura"},
                                           "keyframes": [{"image": "resources/books/processed/b/a/step_01.png", "caption": "1"}]})
    out, counts = merge_mod.project()
    by_id = {t["id"]: t for t in out}
    assert by_id["tech:a"]["status"] == "reviewed"
    assert by_id["tech:a"]["name_romaji"] == "fixed"
    assert by_id["tech:a"]["slots"]["technique"] == "kotegaeshi"
    assert by_id["tech:a"]["slots"]["attack"] == "tsuki"   # original preserved
    assert by_id["tech:a"]["keyframes_reviewed"][0]["caption"] == "1"
    assert by_id["tech:a"]["review"]["reviewed_by"] == "person:t"
    assert by_id["tech:b"]["status"] == "provisional"
    assert counts["corrected"] == 1 and counts["unreviewed"] == 1
