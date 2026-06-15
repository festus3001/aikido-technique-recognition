# Lineage Seed Sources (postwar focus)

Reference sources for the `teaches_relationship` edges. Lower confidence than primary
rosters/promotion lists: tag an edge `stated` only where the source states the link
explicitly, otherwise `inferred`. Every edge carries `source` + `retrieved`.

## Backbone
- **Aikido Journal -- "The Principal Disciples of Morihei Ueshiba"** (Pranin chart; 2001,
  updated 2011, modernized 2018). Canonical map of the founder's primary direct students.
  Use as the backbone for first-generation edges. Selections are editorial; note omissions
  (e.g. some Iwama students).
- **Aikido Journal -- "Who were the Shapers of Postwar Aikido?"** (Pranin). Prose on the
  postwar leadership (Kisshomaru Ueshiba, Koichi Tohei, Kisaburo Osawa, postwar uchideshi);
  dates and relationship context.

## Roster + structured edges
- **Wikipedia "List of aikidoka."** People sorted by region; direct students of the founder
  marked with an asterisk (*). Use to create `person` records and flag first-generation.
- **Wikipedia per-teacher infoboxes.** Each article's infobox has `Teacher(s)` and
  `Notable students` fields -- parse systematically into edges. Confirmed examples:
  - Gozo Shioda (Yoshinkan) -> Terada, Kushida, K. Inoue, Makiyama, Chida, Ando, Payet,
    Y. Shioda, Mustard
  - Nobuyoshi Tamura (French line) -> Chassang, Suga, Vural, Martin
  - Bansen Tanaka (Osaka Aikikai) -> Kawahara, Tomita, Ishiyama
  - Mitsugi Saotome (ASU) -> Hiroshi Ikeda, William Gleason
  - Hiroshi Tada -> Masatomi Ikeda
- **Aikido Sangenkai blog (Chris Li).** Lineage/translation material incl. Ueshiba-family
  generations; cross-check and Japanese-source context.
- **Pranin, "Aikido Masters: Prewar Students of Morihei Ueshiba"** (Aiki News, 1993). Prewar
  anchor for the generation above the postwar groups.

## Postwar priority edges
Direct students who built the postwar organizations, then their notable students:
Kisshomaru + Moriteru Ueshiba (Aikikai mainline), Koichi Tohei (Ki Society), Gozo Shioda
(Yoshinkan), Morihiro Saito (Iwama), Nobuyoshi Tamura + the French line, Yamada / Kanai /
Akira Tohei / Chiba (USAF founders), Mitsugi Saotome (ASU), Fumio Toyoda (AAA).

Note: Akira Tohei (Aikikai, Midwest) is NOT Koichi Tohei (Ki Society). Keep distinct.
