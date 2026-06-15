"""The parse structure -- parse, don't classify.

A technique is recovered as filled slots plus a continuous deep-layer embedding,
not a single flat label.
"""

# Surface slots (discrete, compositional):
#   attack      e.g. katate-dori, shomen-uchi, ushiro-ryote-dori
#   technique   e.g. ikkyo, kote-gaeshi, shiho-nage
#   direction   omote | ura  (where applicable)
# Deep layer (continuous):
#   embedding   learned representation of connection/timing/kuzushi quality
#
# TODO(agent): TechniqueParse dataclass (slots + confidences + deep embedding).
# TODO(agent): grammar/validity constraints (which slot combinations are well-formed).
