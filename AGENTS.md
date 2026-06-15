# AGENTS.md -- Aikido Technique Recognition (ATR)

Model-agnostic context for any AI coding/writing assistant working on this project.
Read this first. It defines what the project is, how to name things, how to write, and
what state the work is in.

---

## Project

**Aikido Technique Recognition (ATR)** -- a prototype system that watches video of aikido
practice and recovers a structured description of the technique being performed (attack,
technique, direction such as omote/ura), with both partners (nage and uke) modeled together.

**Core hypothesis.** A technique's identity is not fully contained in the mechanical motion
of the limbs. Meaningful structure -- timing, coordination, the coupling between partners,
intent -- sits above the raw joint kinematics. The system measures physical movement as a
starting point, then looks for the higher-order structure above it. This is treated as a
testable claim with precedent in movement science, not a mystical one.

**Framing: parse, don't classify.** A technique name (e.g. "katate-dori shiho-nage omote")
is compositional -- attack + technique + direction. The system should recover the parts
(slot-filling / structured prediction), not emit one flat label. Payoffs: compositional
generalization to unseen attack-technique pairings (critical for a small dojo dataset), and
legible errors (right technique / wrong attack is a near miss a teacher can judge).

**Stance toward existing collections.** ATR enters the field as a peer that contributes
back: it interoperates with existing stores on the terms their holders set, and returns
structure to them. Grounded in CARE (collective benefit, authority to control,
responsibility, ethics) alongside FAIR for interoperability. The teacher's correction is
recognized contribution and the only source for the deep/qualitative layer -- respect and
research are the same thing. See atr_04_governance_thread.

**Two layers.**
- Surface: the named slots (attack, technique, direction) -- recoverable with current methods.
- Deep: the qualities a teacher reads but the names don't carry (connection/musubi, timing,
  quality of kuzushi). Better modeled as a learned continuous representation than a discrete
  label. This deeper layer is the research frontier and the reason the project exists.

---

## Audience

Primary reader is a master aikido teacher with deep domain expertise but little AI/ML
background. Secondary: a technical reader they may forward work to. Write so the first
reader is never lost and the second reader is never insulted.

---

## Writing conventions (STRICT)

- **No em dashes.** Use double hyphens ( -- ) instead. This is a hard rule.
- **No icons, emoji, or decorative symbols** in deliverables.
- **No "AI-tell" language.** Avoid: delve, leverage, robust, seamless, "rich tapestry",
  "it's worth noting", "in plain terms", hollow openers, padding. Write plainly and directly.
- **No funding/grant framing** unless explicitly requested.
- Prefer markdown over Word documents unless a Word doc is specifically asked for.
- Concise, dense outputs. Directional guidance over prescriptive specs.
- Honest technical accuracy. Call out confident errors directly; flag anything cited from
  memory vs. verified against a primary source.

---

## Stack & platform policy

Local-first. The model comes to the data; collections stay on holder infrastructure
where possible. Platforms: macOS (Apple Silicon) and Linux only -- no Windows, no CUDA
assumption. Acceleration: MPS on Mac, CUDA on Linux if present, CPU fallback always works.

- Builder / analyst surface: Python via conda (Miniforge), notebook-driven, PyTorch.
  Install torch via pip inside the conda env; native arm64 Python is mandatory on Mac.
  Watch the macOS 26 MPS-availability regression; detect device at runtime.
- Contributor tools + demo sites: FastAPI (Python) backend, React (Vite + TS) frontend.
- Training compute: ATR models are small; a single 4090/A100 suffices. Holder data trains
  locally only (Linux+CUDA / Mac+MPS). Cloud GPUs only for non-sensitive runs; protected
  collections never go to multi-tenant cloud.
- Demos: Technique Lookup (flagship), Compare, Contribution loop.
Full detail in atr_06_toolchain_stack.

## Asset naming convention (STRICT)

Format: `atr_{NN}_{name}_{class}.{ext}`

- `atr` -- project stem (Aikido Technique Recognition)
- `NN`  -- two-digit index, zero-padded (01, 02, ...)
- `name` -- snake_case descriptive name (e.g. domain_graph, overview, litreview)
- `class` -- asset class: text | graph | data | code | slides
- Do not double up fields (no `domain_graph_graph`).
- Build/source scripts may append a role: e.g. `atr_01_overview_build.js`.

Current assets:
Ordered introductory -> technical. Each document exists as both markdown (working source)
and docx (readable copy) in docs/. The repo is now the source of truth (local Claude setup).
- `docs/atr_01_overview` -- project overview and front door; contains the document index
- `docs/atr_02_roadmap` -- staged project roadmap, phase by phase
- `docs/atr_03_onboarding_teacher` -- Start Here for master teachers
- `docs/atr_04_governance_thread` -- governance & stakeholder thread
- `docs/atr_05_domain_graph.svg` -- domain graph figure (SVG only)
- `docs/atr_06_toolchain_stack` -- toolchain & stack spec
- `docs/atr_09_book_ingestion` -- book scanning/ingestion pipeline spec
- `docs/atr_10_source_bibliography` -- candidate printed sources for taxonomy bootstrap
- `docs/atr_11_lineage_tree` -- provisional aikido lineage tree (data-first)
- `docs/atr_12_federation_map` -- US federation & dojo map (USAF, Ki Society, AAA/AAI, Shin Kaze, Midwest)
- `docs/atr_13_datamap_crawl` -- data-map schema + crawl plan + Claude Code prompt
- `docs/atr_14_movement_language` -- symbolic aikido movement language (AML): spec (kineme/motif/phrase)
- `CLAUDE.md` / `AGENTS.md` -- this file (same content, two names for tool compatibility)

Next free index: 15.

---

## Graphics

- SVG is the source of truth. Do NOT keep rendered PNGs in the project; regenerate on demand.
- Domain graph aesthetic: serif type, warm paper background, three anchor domains at center
  (aikido/budo red, movement science green, AI/ML blue), concentric tiers (on the path /
  complementary / adjacent fields), labeled edges naming what each connection contributes.

---

## Repository layout (local Claude setup)

The repo is the source of truth. Key directories:
- `docs/`       -- project documents, each as paired .md (working source) + .docx (readable),
                   plus the domain graph .svg. Edit the markdown; regenerate docx on build.
- `schema/`     -- the shared data contract (skeleton, parse, contribution).
- `builder/`    -- Python/conda model-building surface.
- `contributor/`-- FastAPI backend.
- `web/`        -- React contributor UI and demos.
- `tools/`      -- project tooling. `tools/crawler/` builds the lineage/federation data map
                   (see docs/atr_13_datamap_crawl and tools/crawler/PROMPT.md); writes to data/map/.
- `resources/`  -- ingested source material, gitignored/DVC-tracked, local-first:
                   `resources/books/{raw,processed}` (TIFF masters -> PDF/A + OCR per
                   atr_09), `resources/videos/{raw,processed}` (footage -> pose data per
                   atr_06). Holder collections never leave holder/project hardware.
- `data/`       -- DVC-tracked datasets. `data/map/` holds the crawler's JSON output.
- `deploy/`     -- local-first docker-compose.

## Onboarding (per cohort)

One Start Here document per cohort. Tone: respect domain expertise, assume only basic
computer skills, no jargon without grounding, peer/contribution stance lived in tone.
Tool recommendation: a general assistant (Claude or ChatGPT), interchangeable, one is
enough. Workflow-agnostic. Contribution guidance from teachers is text or image only;
video/media handled separately by targeted ingestion sub-projects per source and schema.
Cohorts still to write: builders/analysts, contributor-tool users, others as identified.
Prompt-crafting reference currently folded into the teacher doc; promote to a shared
asset if later cohorts need the same text.

## Document state (atr_01_overview)

Sections, in order: Premise; Scientific Basis; Parsing Technique; What It Does; How It Works;
Why the Motion Focus Matters; What the Prototype Will Demonstrate; What It Needs From the
Dojo; Future Uses (Preservation and Archive; Research and Cross-Style Study); Capturing Deep
Motion Context; Stance; Further Reading; References.

---

## References (all verified against primary sources)

Scientific basis
- Johansson, G. (1973). Visual Perception of Biological Motion and a Model for Its Analysis.
  Perception & Psychophysics, 14(2), 201-211.
- Bernstein, N. (1967). The Co-ordination and Regulation of Movements. Pergamon Press.
  (Origin of the degrees-of-freedom problem.)
- d'Avella, A., Saltiel, P., & Bizzi, E. (2003). Combinations of muscle synergies in the
  construction of a natural motor behavior. Nature Neuroscience, 6, 300-308.

Technical methods
- Yan, S., Xiong, Y., & Lin, D. (2018). Spatial-Temporal Graph Convolutional Networks for
  Skeleton-Based Action Recognition. AAAI. arXiv:1801.07455.
- Zhu, W., Ma, X., Liu, Z., Liu, L., Wu, W., & Wang, Y. (2023). MotionBERT: A Unified
  Perspective on Learning Human Motion Representations. ICCV. arXiv:2210.06551.
- Shahroudy, A., Liu, J., Ng, T.-T., & Wang, G. (2016). NTU RGB+D: A Large Scale Dataset for
  3D Human Activity Analysis. CVPR, 1010-1019. (Includes two-person mutual actions.)

Verification rule: any new citation must be confirmed against a primary source before it
enters a deliverable. Mark unverified items clearly.

---

## Domain map (for orientation)

Anchors: aikido/budo, movement science, AI/ML for motion.
On the path: biological motion perception; pose estimation/CV; joint-action coordination;
action segmentation.
Complementary (method donors): action quality assessment (AQA); dance computing (Laban,
AIST++); sports performance analysis; compositional ML; embodied cognition.
Adjacent: surgical/rehab motion analysis; affective computing; cultural/intangible heritage;
robotics/imitation learning.

---

## Open questions / working threads

Supervisor (decisions + open items)
- OPEN: embed domain graph inside the doc, or keep standalone.
- OPEN: literature review as a doc section vs. its own asset.
- OPEN: how far to develop the deep/qualitative layer in writing (currently named, not built out).
- OPEN: final audience register (teacher-only vs. teacher + technical forward).

Literature review (status)
- Tier 1 (verified): the 6 references above.
- Tier 2 (named, not yet pulled): CTR-GCN / InfoGCN / 2s-AGCN (velocity, multi-stream);
  AQA survey; AIST++ / computational Laban; compositional / zero-shot action recognition;
  two-person interaction modeling beyond NTU.
- DECISIVE OPEN QUESTION: has anyone done computational aikido / judo / BJJ? This defines the
  project's novelty claim and should be resolved before the review is framed.

---

## Data reality (known constraints)

- Aikido knowledge already lives in established collections and lineages with their own
  stewards. ATR interoperates with these rather than building a corpus from scratch.
- Expect class imbalance; the omote/ura split is often harder than the technique family.
- Technique segmentation (start/end boundaries) is itself a hard sub-problem.
- Train with viewpoint augmentation; dojo camera angles vary.
- Model both bodies; many techniques are only distinguishable by uke's response.
