"""Canonical 3D skeleton -- the FAIR interoperability contract.

Every collection maps to this schema; every surface imports it. This is the one
representation all of ATR agrees on. Define joint set, ordering, and the per-frame
channels here. A coding agent should fill in the concrete joint list and dataclasses.
"""

# TODO(agent): define canonical joint set + ordering (document the source convention).
# TODO(agent): MotionSequence dataclass -- per-frame: position, velocity, acceleration,
#              6D joint rotation, root trajectory + root angular velocity.
# TODO(agent): two-body relational channels (nage/uke contact, grip, line of force).
