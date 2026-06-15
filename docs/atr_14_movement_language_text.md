# Aikido Movement Language (AML)

Specification, draft

A symbolic language for describing aikido movement: fine enough to isolate a single articulation,
structured enough to chain those isolations into motifs, and motifs into whole techniques. AML is
the missing layer between the measured skeleton and the named technique.

---

## Premise

ATR holds that a technique's identity lives in structure above raw joint kinematics, and that a
technique name is built from parts (attack, technique, direction). The system already plans for
the two ends of this: the canonical skeleton that measures movement (schema/skeleton.py) and the
parse that names it (schema/parse.py). What is missing is the layer in between -- a way to say
*how* the body moves, in units that compose.

A teacher does not read a technique as joint coordinates, nor as a single label. They read it as a
sequence of recognizable actions: an entry, a turn, a moment of unbalancing, a throw. AML is an
attempt to write that down in symbols that a teacher can read and a machine can ground. It is a
descriptive language, not a scoring system and not the deep qualitative layer; it gives those
layers something structured to attach to.

This document is the design specification. The vocabulary it defines is seeded by hand and primed
from books, and every part of it is provisional and subject to teacher correction.

---

## Where AML sits

Three layers, bottom to top:

- **Measured layer (skeleton).** Joints, 6D rotation, velocity, acceleration, and the two-body
  relational channels, per schema/skeleton.py. Continuous, machine-measured, not symbolic.
- **Symbolic layer (AML).** Discrete, compositional units that name what the body is doing. This
  document.
- **Named layer (parse).** The technique's slots -- attack, technique, direction -- per
  schema/parse.py, plus the deep continuous embedding for the qualities names omit.

AML is the discrete, compositional surface of *motion*. It feeds the parse (a technique is a
pattern of AML units) and it gives the deep layer a structured scaffold rather than raw frames.

---

## Frame of reference

All AML symbols are read in a nage-relative frame so that the same technique reads the same
regardless of camera angle or which way the pair happens to face:

- **Primary axis:** the line between the two partners (the ma-ai axis). "Forward" is along it
  toward uke; "back" is away.
- **Sides:** omote (front, entering ahead of uke) and ura (rear, turning behind). Side is a
  first-class direction in AML because the omote/ura split is often the hard distinction.
- **Posture:** kamae and hanmi (which foot and hand lead) set the starting configuration a phrase
  is written against.

Where a symbol needs a frame other than nage's body (the ground, or uke's body), it is tagged
explicitly.

---

## The three tiers

| Tier | Unit | Nature | Lever |
|------|------|--------|-------|
| 1 | **Kineme** | atomic, closed set | precision / depth |
| 2 | **Motif** | conventional bundle, open lexicon | coverage / width |
| 3 | **Phrase** | technique over budo phases | structure / chaining |

Tier 1 is small and fixed so that descriptions are precise and reproducible. Tier 2 is open and
grows as books and teachers add to it. Tier 3 is the syntactic backbone that turns motifs into a
technique. The separation is deliberate: depth comes from the closed atomic alphabet, width comes
from the open motif lexicon. They do not compete.

---

## Tier 1: Kinemes

A **kineme** is the smallest isolable unit of movement: one articulator doing one action, with
parameters and a dynamic. It is the phoneme of the language.

A kineme has four parts:

- **Articulator** -- the body part: left/right foot, koshi (center/hips), spine, left/right
  shoulder, elbow, wrist (tegatana, the hand-blade), head, or whole-body (tai).
- **Action** -- one of a closed set: rotate, translate (step/shift), flex/extend, pivot,
  drop/rise, open/close.
- **Parameters** -- axis (vertical, horizontal, sagittal, or a named spiral), direction (toward or
  away along the ma-ai axis; omote or ura side), and a quantized magnitude (eighth, quarter, half,
  full turn for rotations; near, mid, far for steps).
- **Dynamic** -- a four-value effort tuple borrowed from Laban: weight (light or strong), time
  (sudden or sustained), space (direct or indirect), flow (bound or free). This is where the
  *quality* of a movement enters the symbolic layer.

Illustrative readable form (this is the rendering; the canonical form is the schema):

```
wrist.R : evert / half / ura  :: strong sudden direct bound
foot.L  : pivot / half / -    :: light sustained direct free
koshi   : drop  / quarter / - :: strong sustained direct bound
```

### Kinematic signature

Each kineme also carries a **kinematic signature**: a predicate over the skeleton channels that
says when the kineme is present in measured motion. For example, a tenkan-type foot pivot is
present when the support foot is stationary while root angular velocity about the vertical exceeds
a threshold over a time window. Signatures make AML two-directional: a person can write a kineme,
and a machine can detect it. Until the joint set is pinned in schema/skeleton.py, signatures are
written as specifications, not code.

The kineme alphabet is intended to stay small -- on the order of dozens, not hundreds. New
*expressiveness* comes from composition and from the motif lexicon, not from adding kinemes.

---

## Tier 2: Motifs

A **motif** is a named, conventional bundle of kinemes -- simultaneous, sequential, or both --
that aikido already names or that recurs across techniques. Motifs are the morphemes of the
language. Examples (provisional):

- **irimi** -- entering: a forward foot translation with the center advancing.
- **tenkan** -- turning: a pivot plus a half-or-more rotation about the vertical.
- **kaiten** -- wheeling: a rotation that carries an arm or the pair around an axis.
- **tegatana cut** -- a hand-blade descent along a line.
- **kuzushi-down** -- taking balance downward through a contact point.
- **musubi** -- establishing connection at a contact (a coupling motif, see below).
- **ukemi** -- uke's receiving and falling.

Two properties make the motif lexicon the right place for breadth:

- **Open and book-primed.** The lexicon grows by ingesting books (P2). A photo-sequence in a
  manual is read as a candidate decomposition: each step is a motif or a phase boundary.
- **Lineage-tagged.** Motifs vary by school -- an Iwama irimi is not a Yoshinkan irimi. Each motif
  carries a lineage tag (Iwama, Aikikai, Yoshinkan, Ki, or other), which links directly to the
  lineage data map already built in data/map. The same map that records who taught whom can record
  how a motif is performed in that line.

Every motif entry records its source (which book, which teacher) and its status (provisional until
ratified), the same provenance stance used across the project.

---

## Tier 3: Phrases and the phase model

A **phrase** is a technique, or a recognizable segment of one, written as an ordered and possibly
branching composition of motifs over a small set of phases. The phases are the syntactic
constituents -- the grammar of a technique:

1. **de-ai / musubi** -- meeting and connection: the approach, the contact, the moment of joining.
2. **kuzushi** -- unbalancing: balance taken from uke.
3. **tsukuri** -- fitting: nage positions for the throw or pin.
4. **kake** -- execution: the throw or the application of the lock.
5. **zanshin / osae** -- finish: the pin, and remaining awareness.

This five-phase scaffold borrows the kuzushi-tsukuri-kake triad familiar from judo and frames it
with aikido's de-ai/musubi and zanshin. It is a proposed structuring, not received doctrine, and
is subject to teacher ratification.

The named slots attach here. A phrase carries its attack, technique, and direction (the parse
slots), and **omote and ura are written as a branch sharing a common prefix**: the meeting and
often the kuzushi are shared, and the technique diverges at tsukuri or kake. This is not a
notational convenience. It is the structure that lets the system recognize a pairing it has not
seen and that makes a wrong-direction error a near miss rather than a different technique.

---

## Two-body coupling

Aikido is two bodies, and many techniques are only distinguishable by how uke responds. AML treats
this as first-class rather than as an afterthought.

A phrase has **two parallel staves**, one for nage and one for uke, read in the same time. Binding
them are explicit **coupling events**:

- **contact** -- a grip or contact is established (which hand, which target: wrist, elbow, lapel,
  or empty-hand).
- **transmit** -- force or kuzushi passes from one body to the other, with a line of force.
- **release / point-of-no-return** -- the moment after which uke can no longer recover.

The coupling track is what carries the line of force and the timing relationship between the
partners. A technique that looks identical on nage's stave alone can differ entirely on the
coupling track, and that is often where its identity lives.

---

## Composition and grammar

Units combine with a small set of operators:

- `;` **sequence** -- then. One unit follows another in time.
- `+` **chord** -- simultaneous. Units happen together (step while cutting).
- two **staves** -- nage and uke, time-aligned, joined by coupling events.
- `|` **branch** -- variation. A shared prefix splits (omote `|` ura).

These operators apply at every tier: kinemes compose into motifs, motifs into phases, phases into
a phrase. Complexity is built by chaining, not by enlarging the alphabet.

### Representation: one canonical form, derivatives deferred

At bootstrap, AML has one canonical representation: a JSON and dataclass schema
(schema/movement.py plus the vocabularies in data/taxonomy), grounding in skeleton channels.
Well-formedness -- which compositions are valid -- is expressed as validation rules over that
schema, reusing the JSON Schema pattern already proven for the data map
(tools/crawler/schema/entities.schema.json). There is no separate grammar to maintain.

For legibility, a one-way renderer turns the schema into the compact, human-readable form shown in
this document (schema to text), so a teacher can read a phrase without reading JSON.

Deferred on purpose: a *writable* notation with a formal grammar and a parser (text to schema) is
real work, and it only earns its keep once the model is validated and teachers actually need to
author in text. That decision waits until after the kote-gaeshi trial (P4). Until then we keep one
representation and a renderer, not three views and converters.

---

## Crosswalks to existing notation

AML is aikido-native at its core but interoperable by design (FAIR). It does not adopt an existing
system wholesale, because none fits aikido's two-body coupling and phase structure, but it
crosswalks to the systems that solved neighboring problems:

- **Eshkol-Wachman Movement Notation** -- an analytic, joint-angle system that treats a limb as a
  moving radius in quantized spherical coordinates. AML's kineme geometry (articulator, axis,
  magnitude) maps onto it. Borrow: reproducible joint-level isolation.
- **Laban Movement Analysis (Effort and Shape)** -- the dynamics of movement: weight, time, space,
  flow. AML's kineme dynamic tuple is taken directly from Laban Effort. Borrow: the quality
  dimension that the deep layer ultimately wants. Labanotation's multi-column staff also models
  the two-body score layout.
- **Benesh Movement Notation** -- a stave-based system designed for readability by practitioners.
  Borrow: the goal of a notation a non-technical reader can actually use.

These crosswalks are mappings, not dependencies. They let AML exchange with movement-science and
dance-computing work without being bound to any one tradition.

---

## Depth versus width

The central design tension the user named is depth (how finely you can isolate and drill down)
versus width (how much of the art you can name). AML resolves it by splitting the two:

- **Depth** is supplied by Tier 1: a closed, orthogonal kineme alphabet that can describe any
  articulation precisely and can always be drilled into from a motif.
- **Width** is supplied by Tier 2: an open, lineage-tagged, book-primed motif lexicon that grows
  to cover the art without ever enlarging the atomic alphabet.

Because the two levers are separate, adding coverage never costs precision, and adding precision
never requires re-naming the art. Where standards already exist (joint geometry, movement
quality), AML crosswalks to them rather than reinventing, which keeps it close to existing
description structures without inheriting their misfit to aikido.

---

## Grounding in measured motion

AML is meant to round-trip with the skeleton, not float above it:

- **Forward (recognition):** kineme signatures become detectors over skeleton channels (the work
  of builder/atr_motion/represent); a motif is a pattern of detected kinemes; a phrase is a
  sequence of motifs over phases. Video to skeleton to AML to parse.
- **Backward (description):** a teacher or the parser writes AML, which names spans of motion and
  can drive point-light playback for review.

The vocabulary and detectors live in builder/atr_motion/primitives; the dataclasses live beside
schema/skeleton.py and schema/parse.py in a new schema/movement.py; the seeded and book-primed
vocabularies live in data/taxonomy.

---

## What this does and does not claim

- It **is** a descriptive, compositional language for movement, with a closed atomic layer, an open
  motif layer, and a phase-structured technique layer, modeling both partners.
- It **is not** a scoring of quality, nor the deep qualitative embedding itself. It gives those a
  structured surface to attach to.
- The phase model, the kineme alphabet, and every motif are **provisional**. The authority on
  whether a description is right is a teacher reading it back, not the books and not this document.
- Bibliographic details for the notation systems below are cited from memory and should be
  confirmed against primary sources before they enter a published deliverable, per project rule.

---

## Bootstrap status and next steps

- **P0 (this document)** -- the specification. Done.
- **P1 (done)** -- the kineme alphabet: 22 atomic units by hand, each with a kinematic signature,
  as schema/movement.py + schema/movement.schema.json + data/taxonomy/kinemes.json. Deliberately
  small; expressiveness comes from composition, not from enlarging the alphabet.
- **P2** -- prime the motif lexicon and technique taxonomy from books (Saito Iwama corpus, Ueshiba
  Budo) through the atr_09 ingestion pipeline, into data/taxonomy.
- **P3** -- validation rules (well-formedness) over the schema, reusing the JSON Schema pattern,
  plus the one-way readable renderer. A writable notation and parser are deferred past P4.
- **P4** -- the trial: fully transcribe kote-gaeshi (omote and ura) at all three tiers, including
  the coupling track, and check it back with a teacher.
- **P5** -- machine grounding: signatures to detectors, a parse head that predicts motif sequences.

---

## References

Movement notation and analysis (bibliographic details to verify against primary sources):

- Eshkol, N., and Wachman, A. (1958). Movement Notation. Weidenfeld and Nicolson.
- Laban, R., and Lawrence, F. C. (1947). Effort. Macdonald and Evans. (Laban Movement Analysis:
  Effort and Shape; see also Kinetography Laban / Labanotation.)
- Benesh, R., and Benesh, J. (1956). An Introduction to Benesh Movement Notation. A. and C. Black.

Project scientific and technical basis (verified, see atr_01_overview.md):

- Johansson, G. (1973). Visual Perception of Biological Motion. Perception and Psychophysics,
  14(2), 201-211.
- Bernstein, N. (1967). The Co-ordination and Regulation of Movements. Pergamon Press.
- Yan, S., Xiong, Y., and Lin, D. (2018). Spatial-Temporal Graph Convolutional Networks for
  Skeleton-Based Action Recognition. AAAI. arXiv:1801.07455.

---

_ATR · aikido movement language spec · rev 2026-06-12 · draft_
