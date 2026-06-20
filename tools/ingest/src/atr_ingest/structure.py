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
}

_FALLBACK = Section("taijutsu", "technique")  # books without a map yet: behave as before


def section_for(book_id: str, pdf_page: int) -> Section:
    for start, end, sec in _MAPS.get(book_id, []):
        if start <= pdf_page <= end:
            return sec
    return _FALLBACK


def has_map(book_id: str) -> bool:
    return book_id in _MAPS
