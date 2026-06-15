"""Aikido Movement Language (AML) -- data model for Tier 1 (kinemes).

See docs/atr_14_movement_language_text.md. AML has one canonical representation:
these dataclasses plus the JSON vocabularies in data/taxonomy, validated against
schema/movement.schema.json, with a one-way renderer to the readable form. There
is no separate grammar or parser at this stage (deferred past the P4 trial).

A Kineme is a DEFINITION: one articulator + one action + the geometry it admits +
a kinematic signature (a predicate over the canonical skeleton channels, so the
unit is both human-writable and machine-detectable). A KinemeUse BINDS a
definition to a side, magnitude, direction, and effort -- this is what Tier 2
motifs and Tier 3 phrases will compose (later). The kineme alphabet is closed and
deliberately small; expressiveness comes from composition, not from adding units.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
KINEMES_PATH = REPO_ROOT / "data" / "taxonomy" / "kinemes.json"
SCHEMA_PATH = REPO_ROOT / "schema" / "movement.schema.json"


# -- closed enums (the alphabet's dimensions) ------------------------------

class Articulator(str, Enum):
    FOOT = "foot"; KOSHI = "koshi"; SPINE = "spine"; SHOULDER = "shoulder"
    ELBOW = "elbow"; KNEE = "knee"; FOREARM = "forearm"; WRIST = "wrist"
    HAND = "hand"; HEAD = "head"; TAI = "tai"  # tai = whole body


class Action(str, Enum):
    ROTATE = "rotate"; TRANSLATE = "translate"; FLEX_EXTEND = "flex-extend"
    PIVOT = "pivot"; LEVEL = "level"; OPEN_CLOSE = "open-close"  # level = drop/rise


class Axis(str, Enum):
    VERTICAL = "vertical"; SAGITTAL = "sagittal"; LATERAL = "lateral"
    LONGITUDINAL = "longitudinal"; SPIRAL = "spiral"


# magnitude scales a kineme may use; a use picks one value from the relevant scale
TURN = ["eighth", "quarter", "half", "three-quarter", "full"]
EXTENT = ["near", "mid", "far"]
LEVEL = ["low", "mid", "high"]
MAGNITUDE_SCALES = {"turn": TURN, "extent": EXTENT, "level": LEVEL}

# Laban Effort dimensions (the dynamic / quality of a kineme use)
EFFORT = {"weight": ["light", "strong"], "time": ["sudden", "sustained"],
          "space": ["direct", "indirect"], "flow": ["bound", "free"]}

SIDES = ["L", "R", "center", "both"]


# -- dataclasses -----------------------------------------------------------

@dataclass(frozen=True)
class Kineme:
    """A definition: a closed-alphabet atomic movement unit."""
    id: str
    label: str
    articulator: str
    action: str
    axes: list[str]
    signature: str
    magnitude_scale: str | None = None
    directions: list[str] = field(default_factory=list)
    crosswalk: dict = field(default_factory=dict)
    aikido_terms: list[str] = field(default_factory=list)
    source: str = "AML seed (P1)"
    status: str = "provisional"

    @staticmethod
    def from_dict(d: dict) -> "Kineme":
        return Kineme(
            id=d["id"], label=d["label"], articulator=d["articulator"], action=d["action"],
            axes=d["axes"], signature=d["signature"], magnitude_scale=d.get("magnitude_scale"),
            directions=d.get("directions", []), crosswalk=d.get("crosswalk", {}),
            aikido_terms=d.get("aikido_terms", []), source=d.get("source", "AML seed (P1)"),
            status=d.get("status", "provisional"))


@dataclass(frozen=True)
class Effort:
    weight: str | None = None
    time: str | None = None
    space: str | None = None
    flow: str | None = None

    def render(self) -> str:
        vals = [v for v in (self.weight, self.time, self.space, self.flow) if v]
        return " ".join(vals)


@dataclass
class KinemeUse:
    """A definition bound for use in a motif/phrase: side, magnitude, direction, effort."""
    kineme: str                       # id of a Kineme definition
    side: str | None = None
    magnitude: str | None = None
    direction: str | None = None
    effort: Effort | None = None

    def render(self, alphabet: dict[str, Kineme]) -> str:
        """One-way render to the readable token form (schema -> text)."""
        kin = alphabet[self.kineme]
        art = kin.articulator + (f".{self.side}" if self.side and self.side in ("L", "R") else "")
        verb = self.direction or kin.action
        parts = [verb]
        if self.magnitude:
            parts.append(self.magnitude)
        body = "/".join(parts)
        token = f"{art} : {body}"
        if self.effort and self.effort.render():
            token += f" :: {self.effort.render()}"
        return token


# -- loading and validation ------------------------------------------------

def load_kinemes(path: Path = KINEMES_PATH) -> list[Kineme]:
    records = json.loads(path.read_text(encoding="utf-8"))
    return [Kineme.from_dict(r) for r in records]


def validate(kinemes_path: Path = KINEMES_PATH, schema_path: Path = SCHEMA_PATH) -> list[str]:
    """Validate kinemes.json against the JSON Schema. Returns error strings.
    Reuses the same approach as the data map (tools/crawler validation)."""
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print("WARNING: jsonschema not installed; structural load check only.")
        load_kinemes(kinemes_path)
        return []
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    data = json.loads(kinemes_path.read_text(encoding="utf-8"))
    v = Draft202012Validator(schema)
    return [f"{list(e.absolute_path)}: {e.message}" for e in v.iter_errors(data)]


if __name__ == "__main__":
    errors = validate()
    alphabet = {k.id: k for k in load_kinemes()}
    print(f"kinemes: {len(alphabet)} | validation: {'OK' if not errors else f'{len(errors)} errors'}")
    for e in errors:
        print("  ", e)
    # demo the renderer on a few bound uses (the kote-gaeshi defining wrist turn, a tenkan)
    demos = [
        KinemeUse("kineme:forearm-rotate", side="R", magnitude="half", direction="evert",
                  effort=Effort("strong", "sudden", "direct", "bound")),
        KinemeUse("kineme:tai-rotate", side=None, magnitude="half", direction="ura",
                  effort=Effort("light", "sustained", "direct", "free")),
        KinemeUse("kineme:koshi-level", magnitude="low", direction="falling",
                  effort=Effort("strong", "sustained", "direct", "bound")),
    ]
    print("renderer demo:")
    for u in demos:
        print("  ", u.render(alphabet))
