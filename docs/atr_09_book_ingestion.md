# ATR -- Book Ingestion Pipeline

The text-ingestion path that bootstraps the technique taxonomy (Roadmap Phase 1). It turns
printed aikido reference books into a structured, searchable, machine-readable form from
which the taxonomy and surface-layer vocabulary are extracted. This spec covers the scanning
process, the data formats, and the minimum capture standards.

Scope note: the aim is to extract structure and fact -- the technique names, their
classifications, and the relationships among them -- not to reproduce or redistribute the
books. The books are copyrighted works whose authors and publishers hold rights. Capture and
OCR happen on project or holder hardware; scans and derived text are working material, not
published artifacts, and provenance is recorded for every source.

---

## Pipeline overview

1. **Capture** -- scan or photograph each page to an archival master image.
2. **Pre-process** -- deskew, crop, despeckle, normalize tone; derive a working copy.
3. **OCR** -- recognize text, producing a searchable layer plus coordinates and confidence.
4. **Structure** -- parse the recognized text into the taxonomy artifact (names, slots,
   relationships), with page-level provenance back to the source image.
5. **Store and version** -- archival masters, working derivatives, and the structured output
   each versioned, with consent and provenance metadata.

The archival master is kept untouched; everything downstream is derived from it so the
capture is done once and never repeated.

---

## Capture standards (minimum and recommended)

Anchored to FADGI 2023 (the Federal Agencies Digitization Guidelines Initiative), the current
standard for archival digitization, and its star-rating system.

**Resolution**
- Minimum: **400 ppi** for bound text pages. This is the FADGI archival floor and the level
  at which fine print and diacritics survive cleanly for OCR.
- Recommended: **400-600 ppi**. Use 600 ppi for older, rare, or small-type books where
  detail matters; 400 ppi is adequate for modern clean print.
- 300 ppi is acceptable only as a hard fallback for disposable reference where the book is
  common and the text is large and high-contrast. Do not use it for anything to be archived.
- Resolution is measured at the physical page size (true optical ppi), not interpolated.

**Bit depth and color**
- Capture in **24-bit color** (8 bits per channel) even for black-text pages. Color masters
  preserve paper tone, ink variation, diagrams, and annotations, and cost little at these
  sizes. Do not capture text masters in bitonal (1-bit); bitonal destroys the grayscale OCR
  needs and cannot be recovered.
- Grayscale (8-bit) is an acceptable master only for plain text with no color content.

**Targets and quality**
- Aim for **FADGI 3-star** as the working minimum (the NARA preservation-grade threshold)
  and 4-star where the source warrants. Three-star is the level explicitly considered good
  enough for accurate reproduction and OCR.
- Where feasible, include a scale/color target in the capture and verify against FADGI
  metrics; for a lightweight project this can be a periodic check rather than per-page.

**Capture method**
- A flatbed or overhead book scanner is preferred over a phone camera for masters. If a
  camera is used, it must be on a copy stand with even, diffuse lighting, shooting RAW, and
  hit the same effective ppi and FADGI targets.
- Scan facing pages as **single pages**, not spreads, so each page is an independent unit.

---

## File formats

**Archival master**
- **TIFF**, uncompressed or lossless (LZW/ZIP). One file per page. This is the preservation
  master: lossless, widely supported, format-stable. Never JPEG for masters -- lossy
  compression discards detail OCR depends on and degrades on any re-save.
- Embed capture metadata (device, ppi, bit depth, date, operator, source book provenance).

**Working / access derivative**
- **PDF/A** for the per-book searchable document: the page images wrapped with an embedded
  OCR text layer behind them, so the book is full-text searchable while the page image is
  preserved. PDF/A is the archival PDF profile, self-contained and format-stable.
- A parallel lightweight access copy (JPEG or PDF at lower ppi) is fine for quick reading,
  but it is a derivative, never the master.

**Recognized text and structure**
- OCR output retained in a coordinate-bearing format -- **ALTO XML** or **hOCR** -- which
  carries per-word position and confidence, not just flat text. This lets the structuring
  step tie an extracted technique name back to its exact place on the page.
- The final taxonomy artifact is structured data (JSON), versioned, with each entry carrying
  provenance: source book, page, and OCR confidence.

**Summary of the chain**
- Master: TIFF (lossless, per page) ->
- Searchable book: PDF/A (image + OCR text layer) ->
- OCR detail: ALTO XML or hOCR (coordinates + confidence) ->
- Taxonomy: JSON (structured, versioned, provenance-tagged).

---

## OCR

- **Tesseract** (LSTM engine) is the default: open source, self-hostable, runs on project
  hardware, supports 100+ languages and outputs hOCR, ALTO, PDF, and plain text. It keeps the
  text on local infrastructure, consistent with the project's local-first stance.
- For pages where Tesseract struggles (older type, mixed scripts, romaji plus kanji, complex
  layout), a stronger engine -- commercial (ABBYY FineReader) or a VLM-based parser -- may be
  used on non-sensitive material, but the default path stays local.
- Japanese terms matter here: ensure the OCR language set includes Japanese where books carry
  kanji/romaji technique names, and hand-verify the technique vocabulary, since these are the
  exact tokens the taxonomy depends on.
- OCR is never trusted blind. The extracted technique vocabulary is confirmed by teachers in
  Roadmap Phase 2; OCR confidence scores flag low-certainty terms for review.

## Layout and positional capture (critical for technique books)

Aikido instructional books do not read like prose. A single technique is taught as an ordered
sequence of photographs whose reading order is often not simple top-to-bottom or
left-to-right -- frames step diagonally, wrap across columns, or interleave with the text that
governs them. The instructional meaning lives in that order and in the binding between each
photo and its caption. A pipeline that captures flat text plus a loose pile of images destroys
exactly what makes the page a technique. Capturing the positional structure is therefore a
first-class requirement, not an afterthought.

What must be captured per page:
- **Region geometry.** The bounding box of every element -- each photograph, each text block,
  each caption, each figure number -- in page coordinates. This is the raw material for
  recovering order and binding. OCR already yields text-block geometry via ALTO/hOCR; image
  regions must be captured the same way (see embedded-image handling below).
- **Reading order.** An explicit ordered sequence of the photographs for each technique, not
  inferred from raster position alone. Because the layouts are irregular, reading order is
  proposed by layout analysis and then confirmed by a person; it is not trusted from geometry
  heuristics. Frame numbers printed in the book, where present, are the ground truth.
- **Text-to-image binding.** Which caption or instruction governs which photograph, recorded
  as an explicit link between a text region and an image region, not left implicit in
  proximity.
- **Page layout class.** Tag each page by type -- sequence plate (multi-frame technique),
  single captioned plate, prose, mixed -- since each is handled differently downstream.
- **Bilingual handling.** Where Japanese and English appear in parallel, capture both as
  separate, language-tagged regions bound to the same images; do not merge or let one
  overwrite the other.

Practically: run layout analysis (a document-layout model, or PDF/region tooling such as
PyMuPDF for geometry) to propose regions, order, and bindings; persist them as a structured
per-page layout record; then have a person confirm the sequence and bindings for technique
pages. The layout record travels with the page, keyed to the archival master by page and by
region coordinates.

## Embedded image handling

The photographs are the heart of these books and must be captured as first-class objects,
not discarded as OCR background.

- **Extract every page image with its position.** For each photograph, retain the image
  itself plus its bounding box in page coordinates and its membership in the technique
  sequence. Loose extraction without coordinates is not acceptable -- position is what lets
  the sequence be reconstructed.
- **Provenance for masters vs. derived scans.** When re-capturing from the physical book, the
  page master (TIFF, per the standards above) is the source of truth and individual figures
  are cropped from it, preserving their coordinates. When only an existing digital scan is
  available, extract the embedded images at native resolution and record that they are derived
  from a lower-grade source.
- **Do not upsample or "enhance" silently.** Record true source resolution. A 150 ppi JPEG
  figure is labeled as such; it is not interpolated to look like a master.
- **Keep figures lossless downstream.** Cropped figures are stored lossless (TIFF), even when
  the source was JPEG, so no further generational loss is introduced.

## Handling low-grade existing scans

Many aikido books circulate only as low-resolution, lossy, text-layer-less scans (a typical
example: a 137-page book at 150 ppi, RGB, JPEG, no embedded text). The pipeline handles these
without pretending they meet archival grade:

- **Prefer re-capture.** Where the physical book can be obtained, scan it fresh to the capture
  standards above. The existing low-res scan is treated as a finding aid, not a master.
- **Degrade gracefully when re-capture is impossible.** Accept the scan as a clearly labeled
  sub-archival source: record its true resolution and compression, run OCR with the
  understanding that accuracy will be lower, and raise the human-confirmation bar for both the
  technique vocabulary and the page layout.
- **Never relabel a derived scan as a master.** Source grade is part of provenance and follows
  the material through every downstream artifact.

---

## Minimums at a glance

- Resolution: 400 ppi minimum, 600 ppi for rare/small-type. Never below 300.
- Color: 24-bit color master (grayscale only for plain text). Never bitonal.
- Master format: lossless TIFF, one file per page.
- Searchable form: PDF/A with embedded OCR text layer.
- OCR detail: ALTO XML or hOCR with coordinates and confidence.
- Quality: FADGI 3-star minimum, 4-star where warranted.
- Provenance: source, page, device, and operator recorded for every capture.

---

_ATR · book ingestion pipeline · rev 2026-06-08 · draft_
