# Aikido Technique Recognition

Overview

## Project Documents

This overview is the front door. The others, ordered from introductory to technical:

- **atr_02_roadmap** -- the staged path from printed reference to working prototype, phase by phase.
- **atr_03_onboarding_teacher** -- the Start Here guide for master teachers joining the project.
- **atr_04_governance_thread** -- the governance and stakeholder position: rights, reciprocity, and how the project relates to the communities whose knowledge it draws on.
- **atr_05_domain_graph** -- a one-page figure mapping where the research sits and which neighboring fields feed it.
- **atr_06_toolchain_stack** -- the technical specification: builder and analyst environment, contributor tools, deployment, and demo projects.
- **atr_07_repo_scaffold** -- the code repository scaffold, ready to hand to a coding agent.
- **atr_08_agents** -- context file for AI coding and writing assistants: project state, conventions, stance, and stack policy. (Kept as AGENTS.md at the repo root so tools auto-detect it.)

# Premise

An aikido technique's identity is not fully contained in the mechanical motion of the limbs. Decades of movement science support this: people recognize identity, emotion, and intent from sparse moving points alone (Johansson's biological-motion studies), and skilled movement organizes into a few coordinated patterns rather than independent joint actions (motor synergies). The hypothesis is that technique and intent live in this higher-order structure -- timing, coordination, the coupling between partners -- and that a model can capture it. The system measures the movement, then looks for the structure above it.

# The Reference Plane

Increasingly, when someone asks what a thing is, a model answers. "What is ikkyo," "what distinguishes omote from ura" -- these questions are more and more put to an AI system. Models are becoming a default reference for what the art is taken to be.

This happens whether or not the aikido community takes part; the representation forms either way, from whatever has been written down and scraped. The question is not whether models will speak for aikido, but whether that voice is shaped by the people who hold the art or left to a flattened, secondhand version.

This project intervenes at that layer. Working with teachers and existing collections, it grounds what models represent in the art as its custodians understand it -- including the qualities secondhand text loses. Authority runs one way: from the community into the model. The model becomes a faithful reference precisely because it rests on those who do not defer to it. Shaping the signal now, while it is still forming, is the opportunity.

# Parsing Technique

A name like *katate-dori shiho-nage omote* is not a single label but parts filled in: the attack (*katate-dori*), the technique (*shiho-nage*), the direction (*omote*). Since the naming is built from parts, the system should recover the parts, not emit one flat label.

This buys two things. The model can recognize a pairing it has never seen, because it learned each piece separately -- and no single collection covers every combination. And its mistakes stay legible: the right technique with the wrong attack is a near miss a teacher can judge, not simply wrong.

Those parts -- attack, technique, direction -- are the surface. The qualities a teacher reads but the names omit (connection, timing, the kind of kuzushi) are the deeper layer, and that layer is what this project is ultimately after.

# What It Does

The system watches video of aikido and identifies the technique -- ikkyo, kote-gaeshi, shiho-nage -- and whether it is omote or ura. A tool that watches a recording and labels what it sees.

# How It Works

The computer tracks how both partners, *nage* and *uke*, move through space in three dimensions. That motion is the surface, not the substance: it attends not to *where* the body is but to *how* it moves -- the speed of a turn, the spiral of the hands, the moment of kuzushi -- then looks for the patterns raw mechanics do not explain, the timing and connection that give a technique its identity.

It learns as a student does, from many examples, and then recognizes techniques in footage it has not seen.

# Why the Motion Focus Matters

Aikido lives in motion and timing, not static shapes. A photo cannot tell ikkyo from nikyo; the *path and rhythm* can. The prototype is built around capturing this -- entry, blend, throw -- and around the *nage*-*uke* relationship, since many techniques are only distinguishable by how *uke* responds.

# What the Prototype Will Demonstrate

- Recognition of a small set of core techniques from ordinary video
- The omote/ura distinction
- A foundation that grows as more footage is added

# What It Needs

Labeled video -- techniques performed cleanly and named. Such material already exists in established collections, and the system works with it rather than requiring a new corpus. The quality of the labeling shapes how well the system learns, which is where a master teacher's eye matters most.

# Future Uses

## Preservation and Archive

- A searchable library of a school's techniques as performed by senior teachers -- a record of a lineage's style.
- Capturing a teacher's stylistic signatures before they are lost: *how this dojo does ikkyo*, not just that it does.

## Research and Cross-Style Study

- Comparing how the same technique is expressed across schools or lineages.
- Studying the biomechanics of effective kuzushi and blending across many practitioners.

# Capturing Deep Motion Context

A technique's identity lives in structure above the raw joint kinematics -- what a human reads instantly from a moving body but joint positions alone do not capture. This is testable and has precedent: biological-motion research shows intent is legible in movement dynamics, and interpersonal-coordination studies show two coupled bodies produce dynamics neither shows alone. The directions below aim at that structure:

- **Two-body modeling.** Track nage and uke together and model the connection between them -- grip, contact point, line of force. The technique often lives in this link, not either body alone.
- **Long-range timing.** Hold the whole arc of a technique in view at once, so entry and throw read as one connected event.
- **Dynamics as primary signal.** Treat velocity, acceleration, and rotational speed as core inputs -- the spiral and the moment of unbalancing are dynamic events.
- **Intent and flow.** Capture the continuity of movement, the unbroken line from contact to throw, closer to how aikido is taught and felt.

# Scientific Basis

The premise has roots in movement science. Johansson's point-light studies showed that intent and identity are read from motion alone, and the motor-control tradition treats skilled movement as a few coordinated patterns rather than independent joints. Both suggest the meaningful structure sits above the raw mechanics. See the references for sources.

# Stance

Aikido knowledge already lives in established collections, lineages, and their stewards. ATR does not arrive to build the corpus the field was missing; it enters as a peer, interoperating with existing stores on their holders' terms and contributing structure back. This rests on data governance: the CARE principles -- collective benefit, authority to control, responsibility, ethics -- hold that those who hold knowledge keep authority over how it is used, and that any system built on it must return benefit. A teacher's correction is not feedback to a product; it is recognized contribution, and the only way the deepest part of the work can be learned. The respect and the research are the same thing.

# Further Reading

Entry points for understanding the field without a technical background:

- **Skeleton-based action recognition --** the core method. "ST-GCN" (Spatial-Temporal Graph Convolutional Networks) is the foundational paper, treating the body as a moving graph.
- **3D human pose estimation --** reconstructing a moving body in three dimensions from ordinary video, the measured layer the system builds on. "MotionBERT" is a strong recent example.
- **Two-person interaction recognition --** activities defined by the relationship between people (the NTU RGB+D dataset includes mutual actions).
- **Motion representation --** how movement is encoded; "6D rotation representation for neural networks" explains why rotation matters for turns and spirals.
- **Human motion datasets --** "AMASS" and "Motion-X" show how large movement libraries are structured.

# References

**Scientific basis**

- Johansson, G. (1973). Visual Perception of Biological Motion and a Model for Its Analysis. Perception & Psychophysics, 14(2), 201-211.
- Bernstein, N. (1967). The Co-ordination and Regulation of Movements. Pergamon Press.
- d'Avella, A., Saltiel, P., & Bizzi, E. (2003). Combinations of muscle synergies in the construction of a natural motor behavior. Nature Neuroscience, 6, 300-308.

**Technical methods**

- Yan, S., Xiong, Y., & Lin, D. (2018). Spatial-Temporal Graph Convolutional Networks for Skeleton-Based Action Recognition. AAAI. arXiv:1801.07455.
- Zhu, W., Ma, X., Liu, Z., Liu, L., Wu, W., & Wang, Y. (2023). MotionBERT: A Unified Perspective on Learning Human Motion Representations. ICCV. arXiv:2210.06551.
- Shahroudy, A., Liu, J., Ng, T.-T., & Wang, G. (2016). NTU RGB+D: A Large Scale Dataset for 3D Human Activity Analysis. CVPR.

**Governance**

- Carroll, S. R., Garba, I., Figueroa-Rodriguez, O. L., et al. (2020). The CARE Principles for Indigenous Data Governance. Data Science Journal, 19(1):43.

---

_ATR · overview · rev 1 · 2026-06-08 · draft_