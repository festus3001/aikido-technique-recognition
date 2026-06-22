"""Contribution -- governance as data structure (CARE).

Every contribution (a clip, a label, a correction) carries who made it and under what
terms. No write path may bypass attribution. This module defines the provenance base
that the Refinement primitive (schema/refinement.py) and any other authored record build
on, so attribution is uniform across the project.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as _date


# Machine-readable CARE terms attached to a contribution (all optional; absence means
# "unspecified / governed by the collection's default terms").
@dataclass
class Terms:
    authority: str | None = None          # who holds authority to control (person:/org: slug)
    collective_benefit: str | None = None # the benefit returned to the holder/community
    may_train: bool | None = None         # may this be trained on
    flows_back: bool | None = None        # do derived structures flow back to the holder

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict | None) -> "Terms | None":
        return cls(**{k: d[k] for k in d if k in cls.__annotations__}) if d else None


# Attribution carried by every authored record. `basis` records how the claim was made
# (a teacher stating it, an automated pass, an inference, an import) and `confidence`
# reuses the data map's vocabulary so provenance reads the same everywhere.
@dataclass
class Provenance:
    author: str                            # person:<slug> (or org:/tool: for non-human)
    basis: str = "teacher"                 # teacher | auto | inferred | imported
    confidence: str = "stated"             # stated | inferred | contested
    date: str = ""                         # YYYY-MM-DD; filled by today() when blank
    note: str | None = None
    terms: dict | None = None              # CARE terms (Terms.to_dict()), or None

    def __post_init__(self) -> None:
        if not self.date:
            self.date = _date.today().isoformat()

    def to_dict(self) -> dict:
        d = {"author": self.author, "basis": self.basis, "confidence": self.confidence,
             "date": self.date}
        if self.note is not None:
            d["note"] = self.note
        if self.terms is not None:
            d["terms"] = self.terms
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Provenance":
        return cls(author=d["author"], basis=d.get("basis", "teacher"),
                   confidence=d.get("confidence", "stated"), date=d.get("date", ""),
                   note=d.get("note"), terms=d.get("terms"))
