# Aikido Technique Recognition

Governance & Stakeholder Thread

Working thread on the rights, values, and reciprocity owed to the communities whose knowledge ATR draws on. Separate from the technical work by design; this is the ethical and relational architecture of the project.

Status: open / active. Owner decision pending on how prominent this becomes beyond the single paragraph now slated for the overview doc.

## Stance (settled)

ATR enters the field as **a peer that contributes back**. Not a tool offered down to holders, not neutral middleware between collections. A participant that:

- draws on existing collections and the knowledge of those who steward them,

- interoperates with existing stores on the terms their holders set,

- contributes structure back to those holders.

Key insight binding ethics to research: the teacher's correction of what the system recovers is not feedback to a product -- it is recognized contribution, and it is also the only mechanism by which the deep/qualitative layer (the qualities the names cannot carry) can be learned. The respect and the research are the same thing. A peer who gives nothing back does not stay in the loop, and without the loop the deep layer has no source.

## The three traditions this draws on

**1. Data governance / sovereignty -- rights ****&**** authority**

- CARE Principles (Collective Benefit, Authority to Control, Responsibility, Ethics).

Global Indigenous Data Alliance / RDA, 2019. Created as a people-and-purpose counterweight to FAIR, which pushes sharing without accounting for power or origin.

Though developed for Indigenous data, explicitly framed as applying to any community whose knowledge originates the data. Maps cleanly onto a custodial aikido lineage:

a community with custodial knowledge, stewards with authority, a tradition older than the model.

- FAIR (Findable, Accessible, Interoperable, Reusable) -- the interoperability standard ATR needs to "meet existing stores." Pairs with CARE: FAIR gives the technical interoperability, CARE gives the ethics of who controls and benefits. ATR wants both.

- TRUST -- repository-level trustworthiness (note for later, not yet integrated).

**2. Participatory ML -- who shapes the model**

- Founding critique: ML designers hold far more power than those impacted; supervised systems make "the labour of many yield to the design choices of a few."

- Two failure modes to design against:

- Participation washing -- tokenistic participation that launders legitimacy without shifting real power. The teacher-in-the-loop must have actual authority (accept / correct / reject), or it is washing.

- The proxy problem -- using stand-ins for real stakeholders as a labor-saving device.

For ATR: one teacher is not all lineages; do not let one voice proxy the whole field.

**3. Data-as-labor / data dignity -- what is owed**

- Treats contributed knowledge and annotation as labor with value, not free raw material.

- Care-ethics annotation work: make the intellectual, emotional, and embodied labor visible; treat contributors as collaborators whose rights and well-being matter.

- "Embodied labor" framing is unusually apt here -- in aikido the contributed knowledge IS embodied.

## How it anchors ATR (mapping)

- Rights / authority of holders        -> CARE (authority to control, collective benefit)

- Interoperability with existing stores -> FAIR (alongside CARE, not replacing it)

- Teacher in the loop with real power   -> participatory ML (guard against washing, proxy)

- Correction-as-contribution loop       -> data-as-labor / care ethics (recognized labor)

## References (governance thread)

Verified against primary sources this session:

- Carroll, S.R., Garba, I., Figueroa-Rodriguez, O.L., et al. (2020). The CARE Principles for Indigenous Data Governance. Data Science Journal, 19(1):43.

(Origin: Global Indigenous Data Alliance / RDA International Indigenous Data Sovereignty Interest Group, Sept 2019.)

Named from literature, NOT yet verified against primary source -- verify before any deliverable:

- Wilkinson, M.D., et al. (2016). The FAIR Guiding Principles for scientific data management and stewardship. Scientific Data, 3:160018.

- Sloane, M., Moss, E., Awomolo, O., Forlano, L. (2020/2022). Participation is not a Design Fix for Machine Learning. (verify venue/year -- EAAMO/arXiv)

- Birhane, A., et al. (2022). Power to the People? Opportunities and Challenges for Participatory AI. (verify venue/year -- EAAMO)

- Cooper, N. & Zafiroglu, A. (2024). From Fitting Participation to Forging Relationships: The Art of Participatory ML. (participation brokers study)

## Open questions

- How prominent does this become beyond the single overview paragraph -- a full section, a separate governance brief, or a charter the holders themselves co-author?

- Ownership: who holds what ATR produces (the recovered parses, the deep-layer representations)? Holders, project, shared?

- Attribution: how is a lineage's or teacher's contribution credited in outputs?

- Consent model: FPIC-style (free, prior, informed consent) at the collection level?

- Who holds the loop -- is there a governing body, advisory board of teachers, or per-collection agreements?

- TRUST integration for any repository ATR stands up.

## Doc integration

Single paragraph slated for the overview doc (atr_01_overview), placed after "Capturing Deep Motion Context" as a short section. Draft held in the working stream; not yet written into the build script pending placement/title confirmation.

## Deferred technical decisions (from stack spec)

Parked here as working items, not yet decided:

- MotionBERT vs. MediaPipe as the default pose lifter for the pilot (accuracy vs. setup weight).

- W&B (hosted convenience) vs. MLflow local (stricter local-first) for experiment tracking.

- SQLite -> Postgres threshold for contribution records.

- Federated / per-holder deploy vs. single project box for the first pilot.

## Training compute rule (pinned; mirrors stack spec)

- Holder collections never leave holder/project hardware. Train on those locally (Linux+CUDA or Mac+MPS on owned hardware).

- Cloud GPUs (RunPod, Vast.ai, Lambda) permitted only for non-sensitive runs: synthetic, augmented, or public data, and architecture experiments before real collections.

- Hard rule: a protected collection never goes to a multi-tenant / third-party-host cloud.

- Rationale: weights are not the sensitive asset; the collections are. This keeps cheap cloud compute available without breaching CARE (authority to control, collective benefit).

---

_ATR · governance thread · rev 1 · 2026-06-08 · draft_