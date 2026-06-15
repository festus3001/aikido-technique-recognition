"""ATR book-ingestion pipeline.

Turns scanned, bilingual (Japanese + romaji) aikido PDFs into structured data:

  technique records   -> data/taxonomy/techniques.json   (the surface taxonomy)
  keyframe records    -> resources/books/processed/...     (saved photo stills + context)

The instructional photographs are saved as tagged stills -- each carries its
technique name (romaji + native), its step index in the sequence, and its source
(volume/page/bbox). They are ground-truth keyframes for later video analysis: a
frame from a video can be matched to a book still to tag the technique position it
represents. The `pose` and `embedding` fields on a keyframe are the hooks for that
downstream comparison.

Pipeline: render page -> OCR (jpn+eng) -> filter to technique captions -> detect
photo regions -> link caption to ordered photos (the adaptation layer) -> save
keyframes + emit records. Provenance-stamped and provisional, pending teacher
ratification, like the rest of the project.
"""

__version__ = "0.1.0"
