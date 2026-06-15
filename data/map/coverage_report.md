# ATR data map -- coverage report

Provisional and subject to teacher correction. See docs/atr_13_datamap_crawl.md.

## Entity counts

| collection | records |
|---|---|
| persons | 585 |
| organizations | 17 |
| dojos | 376 |
| rank_events | 203 |
| tenures | 13 |
| edges | 60 |

## Promotion-list backbone

- Years captured: 2022-2026 (5 distinct years)
- rank_event records: 203

## Dojos

- Total: 376 (6 anchor)
- With instructor data: 347
- Without instructor data: 29

## Co-presence (pre-promotion-list reconstruction)

- Tenure records: 13
- Overlapping pairs found: 25
- Directional (teacher/student) overlaps -> inferred edges: 12
- Peer overlaps (recorded, not asserted as edges): 13

| dojo | a (role) | b (role) | overlap | directional |
|---|---|---|---|---|
| dojo:aikikai-hombu-dojo | person:akira-tohei (uchi-deshi) | person:morihei-ueshiba (founder) | 1946-1955 | yes |
| dojo:aikikai-hombu-dojo | person:akira-tohei (uchi-deshi) | person:koichi-tohei (chief-instructor) | 1955-1955 | yes |
| dojo:aikikai-hombu-dojo | person:akira-tohei (uchi-deshi) | person:mitsugi-saotome (uchi-deshi) | 1955-1955 | no |
| dojo:aikikai-hombu-dojo | person:akira-tohei (uchi-deshi) | person:yoshimitsu-yamada (uchi-deshi) | 1955-1955 | no |
| dojo:aikikai-hombu-dojo | person:koichi-tohei (chief-instructor) | person:yoshimitsu-yamada (uchi-deshi) | 1955-1964 | yes |
| dojo:aikikai-hombu-dojo | person:mitsugi-saotome (uchi-deshi) | person:yoshimitsu-yamada (uchi-deshi) | 1955-1964 | no |
| dojo:aikikai-hombu-dojo | person:morihei-ueshiba (founder) | person:yoshimitsu-yamada (uchi-deshi) | 1955-1964 | yes |
| dojo:aikikai-hombu-dojo | person:koichi-tohei (chief-instructor) | person:mitsugi-saotome (uchi-deshi) | 1955-1969 | yes |
| dojo:aikikai-hombu-dojo | person:koichi-tohei (chief-instructor) | person:morihei-ueshiba (founder) | 1955-1969 | no |
| dojo:aikikai-hombu-dojo | person:mitsugi-saotome (uchi-deshi) | person:morihei-ueshiba (founder) | 1955-1969 | yes |
| dojo:aikikai-hombu-dojo | person:seiichi-sugano (uchi-deshi) | person:yoshimitsu-yamada (uchi-deshi) | 1957-1964 | no |
| dojo:aikikai-hombu-dojo | person:koichi-tohei (chief-instructor) | person:seiichi-sugano (uchi-deshi) | 1957-1965 | yes |
| dojo:aikikai-hombu-dojo | person:mitsugi-saotome (uchi-deshi) | person:seiichi-sugano (uchi-deshi) | 1957-1965 | no |
| dojo:aikikai-hombu-dojo | person:morihei-ueshiba (founder) | person:seiichi-sugano (uchi-deshi) | 1957-1965 | yes |
| dojo:aikikai-hombu-dojo | person:kazuo-chiba (uchi-deshi) | person:yoshimitsu-yamada (uchi-deshi) | 1958-1964 | no |
| dojo:aikikai-hombu-dojo | person:kazuo-chiba (uchi-deshi) | person:seiichi-sugano (uchi-deshi) | 1958-1965 | no |
| dojo:aikikai-hombu-dojo | person:kazuo-chiba (uchi-deshi) | person:koichi-tohei (chief-instructor) | 1958-1966 | yes |
| dojo:aikikai-hombu-dojo | person:kazuo-chiba (uchi-deshi) | person:mitsugi-saotome (uchi-deshi) | 1958-1966 | no |
| dojo:aikikai-hombu-dojo | person:kazuo-chiba (uchi-deshi) | person:morihei-ueshiba (founder) | 1958-1966 | yes |
| dojo:aikikai-hombu-dojo | person:mitsunari-kanai (uchi-deshi) | person:yoshimitsu-yamada (uchi-deshi) | 1959-1964 | no |
| dojo:aikikai-hombu-dojo | person:mitsunari-kanai (uchi-deshi) | person:seiichi-sugano (uchi-deshi) | 1959-1965 | no |
| dojo:aikikai-hombu-dojo | person:kazuo-chiba (uchi-deshi) | person:mitsunari-kanai (uchi-deshi) | 1959-1966 | no |
| dojo:aikikai-hombu-dojo | person:koichi-tohei (chief-instructor) | person:mitsunari-kanai (uchi-deshi) | 1959-1966 | yes |
| dojo:aikikai-hombu-dojo | person:mitsugi-saotome (uchi-deshi) | person:mitsunari-kanai (uchi-deshi) | 1959-1966 | no |
| dojo:aikikai-hombu-dojo | person:mitsunari-kanai (uchi-deshi) | person:morihei-ueshiba (founder) | 1959-1966 | yes |

## Lineage sources pending live extraction (Phase E)

- Aikido Journal -- "The Principal Disciples of Morihei Ueshiba" (Pranin chart; 2001,
- Aikido Journal -- "Who were the Shapers of Postwar Aikido?" (Pranin). Prose on the
- Wikipedia "List of aikidoka." People sorted by region; direct students of the founder
- Wikipedia per-teacher infoboxes. Each article's infobox has `Teacher(s)` and
- Aikido Sangenkai blog (Chris Li). Lineage/translation material incl. Ueshiba-family
- Pranin, "Aikido Masters: Prewar Students of Morihei Ueshiba" (Aiki News, 1993). Prewar

## Reconcile (name-variant duplicates)

- High-confidence clusters: 29
- Medium pairs (review only): 2

  - high: Alan Gay (person:alan-gay), Alan James Gay (person:alan-james-gay) -> canonical person:alan-james-gay
  - high: Angela Murphy (person:angela-murphy), Angela W. Murphy (person:angela-w-murphy) -> canonical person:angela-w-murphy
  - high: Anthea P. Pascaris (person:anthea-p-pascaris), Anthea Pascaris (person:anthea-pascaris) -> canonical person:anthea-p-pascaris
  - high: Arturo A. Peal (person:arturo-a-peal), Arturo Peal (person:arturo-peal) -> canonical person:arturo-a-peal
  - high: Calvin Blanchard (person:calvin-blanchard), Calvin E. Blanchard (person:calvin-e-blanchard) -> canonical person:calvin-e-blanchard
  - high: Chester Griffin (person:chester-griffin), Chester S. Griffin (person:chester-s-griffin) -> canonical person:chester-s-griffin
  - high: Colleen Hogan (person:colleen-hogan), Colleen M Hogan (person:colleen-m-hogan) -> canonical person:colleen-m-hogan
  - high: Damon Apodaca (person:damon-apodaca), Damon G. Apodaca (person:damon-g-apodaca) -> canonical person:damon-g-apodaca
  - high: David A. Norton (person:david-a-norton), David Norton (person:david-norton) -> canonical person:david-a-norton
  - high: David J. Ross (person:david-j-ross), David Ross (person:david-ross) -> canonical person:david-j-ross
  - high: Eliot Rifkin (person:eliot-rifkin), Eliot W. Rifkin (person:eliot-w-rifkin) -> canonical person:eliot-w-rifkin
  - high: Garn G. Sherman (person:garn-g-sherman), Garn Sherman (person:garn-sherman) -> canonical person:garn-g-sherman
  - high: Gustavo J. Ramos (person:gustavo-j-ramos), Gustavo Ramos (person:gustavo-ramos) -> canonical person:gustavo-j-ramos
  - high: James Constable (person:james-constable), James W. Constable (person:james-w-constable) -> canonical person:james-w-constable
  - high: Jerry B. Zimmerman (person:jerry-b-zimmerman), Jerry Zimmerman (person:jerry-zimmerman) -> canonical person:jerry-b-zimmerman
  - high: Jonathan A. Weiner (person:jonathan-a-weiner), Jonathan Weiner (person:jonathan-weiner) -> canonical person:jonathan-a-weiner
  - high: Josnei Dias (person:josnei-dias), Josnei Macedo Dias (person:josnei-macedo-dias) -> canonical person:josnei-macedo-dias
  - high: Julia Freedgood (person:julia-freedgood), Julia M. Freedgood (person:julia-m-freedgood) -> canonical person:julia-m-freedgood
  - high: Kevin Grace (person:kevin-grace), Kevin P. Grace (person:kevin-p-grace) -> canonical person:kevin-p-grace
  - high: Lenore I. Killam (person:lenore-i-killam), Lenore Killam (person:lenore-killam) -> canonical person:lenore-i-killam
  - high: Michael J. McNally (person:michael-j-mcnally), Michael McNally (person:michael-mcnally) -> canonical person:michael-j-mcnally
  - high: Michael Pak (person:michael-pak), Michael S. Pak (person:michael-s-pak) -> canonical person:michael-s-pak
  - high: Patrick H. Hardesty (person:patrick-h-hardesty), Patrick Hardesty (person:patrick-hardesty) -> canonical person:patrick-h-hardesty
  - high: Paul Glavine (person:paul-glavine), Paul L. Glavine (person:paul-l-glavine) -> canonical person:paul-l-glavine
  - high: Paulo Ivan Volochyn (person:paulo-ivan-volochyn), Paulo Volochyn (person:paulo-volochyn) -> canonical person:paulo-ivan-volochyn
  - medium: Andrew Demko (person:andrew-demko) ~ Andrew L. Demko (person:andrew-l-demko) ~ Andrew P. Demko (person:andrew-p-demko)
  - medium: K. Inoue (person:k-inoue) ~ Kyoichi Inoue (person:kyoichi-inoue)

## Validation

- all records valid (or validator unavailable)

