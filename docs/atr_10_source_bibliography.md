# ATR -- Source Bibliography

Candidate printed sources for the taxonomy bootstrap (Roadmap Phase 1) and inputs to
ingestion prioritization (Phase 3). These are technical and instructional manuals -- the books
that define and catalog technique -- separated from philosophy and biography, which do not
seed the taxonomy. Inclusion here is a candidate list, not a claim of rights: each source must
clear permission and provenance before ingestion, per the governance stance, and the aim is
extraction of taxonomy and fact, not reproduction.

---

## Planned ingestion queue (current)

The concrete set to ingest, machine-readable in `data/taxonomy/sources.json` (each carries a
`performer` person:slug that resolves into the lineage data map, a `lineage` tag, and `status`).
It spans four lineages on purpose, so the taxonomy and the AML motif lexicon capture cross-style
variation rather than one school.

| Source | Lineage | Year | Status |
|--------|---------|------|--------|
| Saito, *Traditional Aikido* (5 vols) | Iwama | 1973-1976 | **ingested** |
| Shioda + Shioda, *Total Aikido: The Master Course* | Yoshinkan | 1996 | planned |
| Shioda, *Dynamic Aikido* | Yoshinkan | 1977 | planned |
| Kisshomaru Ueshiba, *Aikido* | Aikikai | 1985 | planned |
| Yamada, *Aikido Complete* | Aikikai (USAF) | 1981 | planned |
| Tohei, *This Is Aikido* | Ki Society | 1968 | planned |
| Moriteru Ueshiba, *Progressive Aikido: The Essential Elements* | Aikikai | 2005 | planned |
| Kisshomaru + Moriteru Ueshiba, *Best Aikido: The Fundamentals* | Aikikai | 2002 | planned |
| Moriteru Ueshiba, *The Aikido Master Course: Best Aikido 2* | Aikikai | 2003 | planned |

All eight planned authors already resolve as `person:` nodes in `data/map`, so each ingested
observation links to its performer and lineage (the C3 observation-provenance model, atr_15).
Per-volume year and ISBN for newly acquired books are confirmed at acquisition, the way the
Saito volumes were read from their colophons. Rights clear before ingestion. The fuller
candidate pool below is the reference to draw from as this queue extends.

---

## English-language lineage

**Morihiro Saito (Iwama)** -- the most complete technical corpus
- *Traditional Aikido*, 5 volumes (Japan Publications, early 1970s): Vol. 1 Basic Techniques,
  Vol. 2 Advanced Techniques, Vol. 3 Applied Techniques, Vol. 4 Vital Techniques, Vol. 5
  Training Works Wonders.
- *Takemusu Aikido*, ~6 volumes (Aiki News, mid-1990s on): Vol. 1 Background & Basics, Vol. 2,
  Vol. 3 Basics Concluded, Vol. 4 Kokyunage, Vol. 5 Bukidori & Ninindori, plus a Special
  Edition. Vol. 1 alone presents 60+ variations of ikkyo, nikyo, sankyo, yonkyo with 600+
  photographs; Vol. 5 covers tachidori, jodori, jonage, tankendori, ninindori.
- *Budo: Commentary on the 1938 Training Manual of Morihei Ueshiba* -- preparatory exercises,
  basic techniques, tantodori, tachidori, ken tai ken, juken, shumatsu dosa.
- *Aikido: Its Heart and Appearance* (1975).

**Gozo Shioda (Yoshinkan)**
- *Total Aikido: The Master Course* -- widely regarded as a leading technical manual.
- *Aikido: The Complete Basic Techniques* (Kodansha) -- the important basic techniques.
- *Dynamic Aikido* (Kodansha, 1977).

**Morihei Ueshiba (Founder)** -- foundational technical documents
- *Budo* (1938 technical manual; trans. John Stevens).
- *Budo Renshu* / *Budo Training in Aikido* (1933 illustrated manual).

**Kisshomaru Ueshiba and Moriteru Ueshiba (Aikikai mainline)**
- Kisshomaru Ueshiba, *Aikido* (Hozansha) -- illustrated technique.
- Moriteru Ueshiba, *Best Aikido: The Fundamentals* and *The Aikido Master Course: Best
  Aikido 2* (advanced technique).

**Koichi Tohei (Ki Society)**
- *Aikido: The Arts of Self-Defense* (1960s).
- *This Is Aikido, With Mind and Body Coordinated*.

**Mitsugi Saotome**
- *Aikido and the Dynamic Sphere* (Westbrook & Ratti) -- the classic illustrated introduction.
- *The Principles of Aikido*.

## French-language lineage

**Christian Tissier** -- the central French technical author
- *Aikido Fondamental* series (a French technical encyclopedia): Vol. 1 *Techniques et
  connaissances fondamentales* (fundamental standing base forms); *Techniques superieures*
  (kneeling techniques -- Suwari-waza, Hanmi-handachi-waza -- Koshi-nage, and Tanto-dori);
  *Aiki-jo* (jo techniques); *Techniques avancees* (variations, applications, and techniques
  not usually referenced).
- *Aikido Initiation* -- beginner method: salute, warm-ups, ukemi, base displacements (Tenkan,
  Tai sabaki, Tai no henka) and elementary techniques (Ikkyo omote, Nikyo ura, Kote gaeshi,
  Irimi nage, Juji garami).
- *Aikido* (4Trainer Editions) -- deluxe bilingual French/English volume of art, history,
  technique, and biography.

**Nobuyoshi Tamura** -- foundational French-resident master
- *Aikido* (Chancellerie Europeenne de l'Aikido, 1975) -- 260-page illustrated volume, preface
  by Kisshomaru Ueshiba.
- *Aikido -- Etiquette et transmission* -- addressed primarily to teachers; collects material
  that in Japan came mainly from oral tradition. More transmission/etiquette than technique
  catalog, but foundational.

## The founder's manuals (cross-lineage)

Both 1930s Ueshiba manuals (*Budo*, 1938; *Budo Renshu*, 1933) sit above lineage and are the
root technical documents the later corpora elaborate. Listed under the founder above; noted
here because they anchor the taxonomy across all schools.

---

## Notes on scope and rights

- **Technique vs. philosophy.** Philosophy, biography, and ki-principle titles (e.g. *The
  Spirit of Aikido*, *The Art of Peace*, *Ki in Daily Life*, biographies) are deliberately
  excluded: they do not catalog technique and so do not seed the taxonomy. They may matter
  later for context, not for Phase 1.
- **Rights clear before ingestion.** Every entry is a candidate only. Each must clear
  permission and have provenance recorded before any capture, per the governance stance
  (authority to control, collective benefit). Sources with explicit no-reproduction terms are
  not pursued unless a documented grant is on file.
- **Editions and translations.** Many titles exist in multiple editions, printings, and
  translations; the specific physical copy captured must be recorded in provenance, since
  pagination, photographs, and even technique coverage vary between editions.

## Open items

- **Japanese-only corpus (significant gap).** This list is weighted to English and French.
  A large body of Japanese-language technical manuals is not yet enumerated and likely matters
  for completeness; it needs a dedicated Japanese-source survey, ideally with a
  Japanese-reading teacher-peer.
- **Long tail.** Beyond the canonical authors above there is a wide tail of dojo manuals,
  federation syllabi, and self-published guides. "All known" is not fully attainable from open
  search; this is the canonical core, to be extended as sources surface.
- **Prioritization (Phase 3).** Capture order will favor the most complete, most clearly
  licensed, and most taxonomically broad sources first -- the Saito corpus is the natural
  starting point on completeness grounds.

---

_ATR · source bibliography · rev 1 · 2026-06-15 · draft_