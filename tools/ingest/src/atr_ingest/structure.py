"""Book structure: per-volume section maps that give each page a context and kind.

Saito's "Traditional Aikido" interleaves three domains -- taijutsu (body technique),
aiki-ken (sword), aiki-jo (staff) -- per the books' own subtitle, 剣・杖・体術の理合
("the principle of ken, jo, and taijutsu"). The ingester is otherwise stateless per
page and so (a) mis-tags weapon movements as partner attacks (a jo thrust is not an
attack) and (b) drops the weapon suburi/kata/partner sections entirely, because their
captions (素振り一(1) / 合わせ一(1)) hit no taijutsu lexicon word.

A section map fixes both. Each entry is a pdf-page range carrying:
  context : taijutsu | aiki-ken | aiki-jo            (which domain)
  kind    : technique | suburi | kata | kumi | skip  (how to model the records)
  weapon  : ken | jo | None
  form    : a form name when the section is one named form (e.g. the 31-count jo kata)

Maps are derived from each volume's table of contents and are provisional: the teacher
confirms or corrects section boundaries during review. Page numbers are pdf pages; where
a volume's printed page numbers differ, the offset is noted.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Section:
    context: str          # taijutsu | aiki-ken | aiki-jo
    kind: str             # technique | suburi | kata | kumi | skip
    weapon: str | None = None   # ken | jo | None
    form: str | None = None     # named form this section belongs to, if any
    note: str | None = None

    @property
    def is_weapon(self) -> bool:
        return self.context in ("aiki-ken", "aiki-jo")


# (start_pdf_page, end_pdf_page_inclusive, Section). Ranges are derived from the TOC.
# Vol.1 TOC at pdf p16-18; printed->pdf offset is +2 (TOC "(1)直突き p84" == pdf p86).
_MAPS: dict[str, list[tuple[int, int, Section]]] = {
    "saito-traditional-aikido-vol1": [
        (1,   24,  Section("taijutsu", "skip", note="front matter / foreword / contents")),
        (25,  40,  Section("aiki-ken", "suburi", "ken", note="ken suburi 1-7 + torifuri-ho")),
        (41,  54,  Section("aiki-ken", "kumi", "ken", form="kumitachi", note="剣の合わせ partner sword")),
        (55,  82,  Section("taijutsu", "technique", note="riai taijutsu via ken principle, incl kokyu-ho")),
        (83,  123, Section("aiki-jo", "suburi", "jo", form="31-no-jo",
                           note="jo suburi by group (突きの部 ...) -- the components of the 31-count jo kata")),
        (124, 137, Section("aiki-jo", "kumi", "jo", form="kumijo", note="杖の合わせ partner jo")),
    ],
    # Vol.2 "Advanced Techniques": weapons-heavy -- paired sword (組太刀 kumitachi) and its
    # variations, 太刀取り (taking the sword, taijutsu-vs-ken), paired jo (組杖 kumijo), and
    # jo-vs-ken riai. Offset printed->pdf is +5. Back-half boundaries are coarse and provisional.
    "saito-traditional-aikido-vol2": [
        (1,   28,  Section("taijutsu", "skip", note="front matter / foreword / contents")),
        (29,  71,  Section("aiki-ken", "kumi", "ken", form="kumitachi",
                           note="組太刀 + 組太刀変化技 (kumitachi and variations)")),
        (72,  82,  Section("taijutsu", "technique", form="tachi-dori",
                           note="太刀取り -- taking the sword (taijutsu vs ken)")),
        (83,  120, Section("aiki-jo", "kumi", "jo", form="kumijo",
                           note="組杖 (kumijo) + 杖・剣の理合 jo-vs-ken; boundary provisional")),
        (121, 184, Section("taijutsu", "technique",
                           note="remaining body-technique applications; provisional")),
    ],
    # Vol.3 "Applied Techniques": all taijutsu (kokyu-ho variations, then ikkyo..gokyo,
    # shiho-nage, kotegaeshi, kaiten/irimi/tenchi/kokyu-nage, juji-garami, koshi, ushiro).
    # No weapons. Offset printed->pdf is +4. The fix here is conservative captioning.
    "saito-traditional-aikido-vol3": [
        (1,  17,  Section("taijutsu", "skip", note="front matter / foreword / contents / frontispiece")),
        (18, 144, Section("taijutsu", "technique", note="体術 -- kokyu-ho + basic-technique variations")),
    ],
    # Vol.4 "Vital Techniques": taijutsu -- takemusu-aiki variations, then the kaeshi-waza
    # (返し技, counters) section from printed p126 (pdf +4 = 130). Here 突き IS a real attack.
    "saito-traditional-aikido-vol4": [
        (1,   17,  Section("taijutsu", "skip", note="front matter / foreword / contents")),
        (18,  129, Section("taijutsu", "technique", note="武産合気 takemusu variations")),
        (130, 170, Section("taijutsu", "technique", form="kaeshi-waza", note="返し技 counters")),
    ],
    # Vol.5 "Training Works Wonders": Chapters 1-2 are essays (identity of aikido, training
    # method) with no technique catalog -- skipped. Chapter 3 (techniques) begins printed
    # p44 (pdf +4 = 48): grip methods, 固体/柔体/流体 forms, henka, multi-attacker, weapon-taking.
    "saito-traditional-aikido-vol5": [
        (1,  47,  Section("taijutsu", "skip", note="front matter + Ch.1-2 essays (no technique catalog)")),
        (48, 152, Section("taijutsu", "technique", note="Ch.3 技法: forms, henka, multi-attacker, weapon-taking")),
    ],
}

_FALLBACK = Section("taijutsu", "technique")  # books without a map yet: behave as before


def section_for(book_id: str, pdf_page: int) -> Section:
    for start, end, sec in _MAPS.get(book_id, []):
        if start <= pdf_page <= end:
            return sec
    return _FALLBACK


def has_map(book_id: str) -> bool:
    return book_id in _MAPS
