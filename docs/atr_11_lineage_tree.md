# ATR -- Aikido Lineage Tree

A data-first map of who studied under whom: the founder, his direct students, and the major
branch-founders the project already references. It exists to support prioritization (which
teacher-peers connect to which collections and styles) and to be ratified and extended by
teachers in Roadmap Phase 2.

**Provisional.** Aikido lineage is contested. Durations, the depth of a given
student-teacher relationship, and which line "represents" the founder are matters of live
disagreement between organizations. Everything below is drawn from public record as a
starting scaffold, not an authoritative ruling. It is meant to be corrected. Where this tree
is wrong, a teacher's correction governs, and that correction is a recorded contribution.

Scope: the trunk and first branches -- the founder, his direct deshi, and the branch-founders
cited in the source bibliography. It thins deliberately after the first generation; deeper
and more recent branches are left for contribution rather than guessed at.

---

## Data model

Each person is an entry with:
- `name` -- common romanized name
- `lineage` / `organization` -- the school or federation associated with them
- `teacher(s)` -- who they studied under within aikido
- `notes` -- role, dates where firmly known, relationship caveats
- `status` -- provisional (default) until teacher-ratified

The authoritative form is structured data (to live in the repo schema as a lineage record).
The outline below is the human-readable view of that data.

---

## Root

**Morihei Ueshiba (O-Sensei)** -- founder of aikido.
- Lineage: root of all branches.
- Teacher (pre-aikido): Sokaku Takeda (Daito-ryu Aiki-jujutsu) -- the principal martial
  antecedent, noted for context; Daito-ryu is ancestor art, not aikido itself.
- Notes: developed aikido across the prewar (1930s, *Budo Renshu* 1933, *Budo* 1938) and
  postwar periods. All entries below trace to him directly or through his direct students.

## First generation -- direct students of the founder

**Kisshomaru Ueshiba** -- son of the founder; Aikikai mainline (Second Doshu).
- Teacher: Morihei Ueshiba.
- Notes: consolidated and led postwar Aikikai; author of illustrated technique works.

**Morihiro Saito** -- Iwama lineage.
- Teacher: Morihei Ueshiba (Iwama, from 1946; long-term uchi-deshi and caretaker of the Aiki
  Shrine).
- Notes: foremost authority on the Iwama weapons-and-body-arts curriculum; author of the most
  complete technical corpus (*Traditional Aikido*, *Takemusu Aikido*).

**Gozo Shioda** -- founder of Yoshinkan.
- Teacher: Morihei Ueshiba (prewar deshi).
- Notes: established Yoshinkan as an independent style; emphasized basics and precision.

**Koichi Tohei** -- founder of the Ki Society (Shin Shin Toitsu Aikido).
- Teacher: Morihei Ueshiba.
- Notes: was chief instructor at Aikikai Hombu before departing to found the Ki Society;
  emphasis on ki principles.

**Nobuyoshi Tamura** -- French/European line (Aikikai).
- Teacher: Morihei Ueshiba (uchi-deshi from the early 1950s).
- Notes: moved to France in 1964; central to the development of aikido in France and Europe;
  author of French-language works.

**Mitsugi Saotome** -- Aikikai (United States; ASU).
- Teacher: Morihei Ueshiba.
- Notes: founded the Aikido Schools of Ueshiba in the United States; author of widely used
  technical and principle works.

(Other documented first-generation deshi -- e.g. Saotome's contemporaries and the wider
prewar/postwar uchi-deshi group -- are intentionally omitted here pending the fuller survey;
their absence is a gap to fill, not a judgment.)

## Second generation (selected, cited in the project)

**Moriteru Ueshiba** -- Aikikai mainline (Third Doshu).
- Teacher: Kisshomaru Ueshiba (and the founder, as a child).
- Notes: current head of the Aikikai mainline; author of *Best Aikido* technical works.

**Christian Tissier** -- French line (Aikikai, FFAAA).
- Teacher(s): trained at Aikikai Hombu (where he was a training partner of Moriteru Ueshiba);
  influenced in France by the Tamura/Nakazono milieu.
- Notes: central French technical author; first non-Japanese awarded 8th dan by the Aikikai.

---

## Open items

- **Depth and breadth.** This is the trunk and first branches only. The full first-generation
  deshi group, the Tomiki and Yoshinkan sub-lines, the many national federations, and modern
  shihan and their students are all unrepresented and await contribution.
- **Contested relationships.** Several student-teacher links carry caveats (duration, whether
  a relationship was direct study or seminar contact). These are flagged in `notes` and must
  be confirmed in Phase 2.
- **Japanese-source and oral record.** Much lineage detail lives in Japanese-language sources
  and oral tradition not captured here; a Japanese-reading teacher-peer is needed for accuracy.
- **Ratification.** No entry should be treated as settled until reviewed by teachers. The tree
  ships as a draft scaffold specifically so it can be corrected.

---

_ATR · lineage tree · rev 2026-06-08 · draft_
