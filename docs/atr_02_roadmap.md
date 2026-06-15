# Aikido Technique Recognition

Roadmap

A staged path from printed reference to working prototype. Each phase produces something usable and de-risks the next. Phases overlap; the order reflects dependency, not a strict sequence, and no dates are fixed while the work is in draft.

# Phase 0 -- Foundations

The project's own documents and conventions: overview, governance stance, toolchain spec, repo scaffold, onboarding. Mostly complete. Establishes how the work is done before the work scales.

# Phase 1 -- Taxonomy bootstrap from printed matter

Ingest a small set of canonical aikido texts to establish the technique taxonomy and the surface-layer vocabulary -- the attack, technique, direction, and form slots and the relationships among them. The aim is structure and fact, not the reproduction of any book's text. Output: a structured, versioned taxonomy artifact with provenance recorded.

# Phase 2 -- Taxonomy confirmation with teachers

Put the bootstrapped taxonomy in front of master teachers for correction and ratification. This is the first real contribution loop: the taxonomy is proposed, teachers confirm or correct, and the corrections are recorded as attributed contributions. It resolves disagreements -- naming, the omote/ura boundary, lineage variation -- before any video is touched, and it means the first teacher contribution happens on text, which fits the way teachers are asked to work. Output: a teacher-ratified taxonomy.

# Phase 3 -- Video ingestion targeting and prioritization

Identify candidate video sources and collections and assess each for licensing, quality, viewpoint, and coverage against the taxonomy. Prioritize sets that fill the most taxonomy cells cleanly and whose holders are willing peers. Stand up the per-source ingestion sub-projects. Output: a prioritized ingestion plan and the first source agreements.

# Phase 4 -- First motion data and analysis

Run the prioritized sources through pose extraction into the canonical skeleton schema; build the representation store and the motion-primitives library. Test the core hypothesis qualitatively -- whether higher-order structure separates techniques -- before committing to model training. Output: a first labeled motion dataset and an analytical read on the hypothesis.

# Phase 5 -- First model

Train the parse-don't-classify model on the surface slots, evaluated on slot accuracy and compositional generalization to unseen attack and technique pairings. The deep, qualitative layer begins here but is not expected to be solved. Output: a model that recovers the surface parse on held-out footage.

# Phase 6 -- Beta prototype delivery

The Technique Lookup demo, served locally, with the contribution loop live: a teacher can look at a recovered parse and correct it. Delivered to a small set of teacher-peers for real use. Output: a working first prototype and a running contribution loop.

# Phase 7 -- Deepening

Ongoing. Grow taxonomy coverage as more sources join; develop the deep, qualitative layer using accumulated teacher corrections; extend to the Compare demo and others; broaden cohorts beyond master teachers. Output: a system that improves as the community contributes.

# Threads that run across phases

- **Governance and consent.** A machine-readable terms and consent model for each source, established as sources join, not retrofitted.
- **Evaluation sets.** The teacher-agreement metric needs a held-out evaluation set built deliberately, with teachers, rather than assembled after the fact.
- **Cohort onboarding.** Builder and analyst onboarding timed to Phase 4; contributor-tool onboarding timed to Phase 6.

---

_ATR · roadmap · rev 2026-06-08 · draft_
