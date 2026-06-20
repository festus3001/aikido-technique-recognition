"""Caption detection and parsing.

OCR of a photo-dominated page returns the real technique caption mixed with noise
from the halftone-screened photos. We keep only lines that match the aikido
lexicon, then parse a caption into surface slots (technique / attack / direction /
form-context), folding diacritics and spacing so OCR variants still match
(Kokyū Nage / Kokyu-nage / Kokyunage all hit the same token).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .util import fold, slugify

# canonical slot value -> extra folded spelling variants (the slug itself is always a variant)
TECHNIQUES = {
    "ikkyo": ["ikkajo"], "nikyo": ["nikajo"], "sankyo": ["sankajo"], "yonkyo": ["yonkajo"],
    "gokyo": [], "shiho-nage": ["shionage"], "kote-gaeshi": ["kotegaeshi"],
    "irimi-nage": ["iriminage"], "kaiten-nage": ["kaitennage"],
    "kokyu-nage": ["kokyunage", "kokyonage"], "kokyu-ho": ["kokyuho", "kokyudosa"],
    "tenchi-nage": ["tenchinage"], "koshi-nage": ["koshinage"],
    "juji-garami": ["jujigarami", "jujinage"], "aiki-otoshi": ["aikiotoshi"],
    "sumi-otoshi": ["sumiotoshi"], "kaiten-osae": ["kaitenosae"],
    "hiji-kime-osae": ["hijikimeosae", "udekimeosae", "ude-kime-osae"],
    "ude-garami": ["udegarami"], "kokyu-tanden-ho": ["kokyutandenho"],
}
ATTACKS = {
    "katate-dori": ["katatedori", "katatekosadori", "kosadori"],
    "ryote-dori": ["ryotedori"], "morote-dori": ["morotedori", "katatemorotedori"],
    "kata-dori": ["katadori"], "mune-dori": ["munedori", "muna-dori", "munadori"],
    "ushiro-ryote-dori": ["ushiroryotedori"], "ushiro-eri-dori": ["ushiroeridori"],
    "ushiro-kubishime": ["ushirokubishime"], "ushiro-dori": ["ushirodori"],
    "shomen-uchi": ["shomenuchi"], "yokomen-uchi": ["yokomenuchi"],
    "tsuki": ["chudantsuki", "jodantsuki", "tski"], "kata-dori-men-uchi": ["katadorimenuchi"],
}
DIRECTIONS = {"omote": [], "ura": []}
FORMS = {  # posture / weapon context
    "suwari-waza": ["suwariwaza", "suwari"], "hanmi-handachi": ["hanmihandachi", "handachi"],
    "tachi-waza": ["tachiwaza"], "tachi-dori": ["tachidori"], "jo-dori": ["jodori"],
    "tanto-dori": ["tantodori", "tantotori"], "jo-nage": ["jonage"],
    "buki-waza": ["bukiwaza"], "kumitachi": ["kumitachi"], "kumijo": ["kumijo"],
    "ken-tai-jo": ["kentaijo"], "ki-no-nagare": ["kinonagare"], "kihon": ["kihon"],
}

_SLOTS = {"technique": TECHNIQUES, "attack": ATTACKS, "direction": DIRECTIONS, "form": FORMS}

# Japanese (kanji) names, matched against the raw OCR text -- on these scans the
# Japanese title is often present where the romaji is sparse (esp. Vol.2+ pins,
# named 第一教...第五教). Maps the same canonical slot values.
KANJI = {
    "technique": {
        "ikkyo": ["第一教", "一教", "一ヶ条"], "nikyo": ["第二教", "二教", "二ヶ条"],
        "sankyo": ["第三教", "三教", "三ヶ条"], "yonkyo": ["第四教", "四教", "四ヶ条"],
        "gokyo": ["第五教", "五教", "五ヶ条"],
        "shiho-nage": ["四方投げ", "四方投"], "kote-gaeshi": ["小手返し", "小手返"],
        "irimi-nage": ["入身投げ", "入り身投げ", "入身投"], "kaiten-nage": ["回転投げ", "回転投"],
        "kokyu-nage": ["呼吸投げ", "呼吸投"], "kokyu-ho": ["呼吸法"],
        "tenchi-nage": ["天地投げ", "天地投"], "koshi-nage": ["腰投げ", "腰投"],
        "juji-garami": ["十字絡み", "十字投げ"], "sumi-otoshi": ["隅落とし", "隅落し"],
        "aiki-otoshi": ["合気落とし", "合気落し"],
    },
    "attack": {
        "katate-dori": ["片手取り", "片手取"], "ryote-dori": ["両手取り", "両手取"],
        "morote-dori": ["諸手取り", "諸手取"], "kata-dori": ["肩取り", "肩取"],
        "mune-dori": ["胸取り", "胸取"], "ushiro-ryote-dori": ["後ろ両手取り", "後両手取り"],
        "ushiro-dori": ["後ろ取り", "後取り"], "shomen-uchi": ["正面打ち", "正面打"],
        "yokomen-uchi": ["横面打ち", "横面打"], "tsuki": ["突き"],
    },
    "direction": {"omote": ["表"], "ura": ["裏"]},
    "form": {
        "suwari-waza": ["座り技", "坐り技", "座技", "居取り"], "hanmi-handachi": ["半身半立", "半身半立ち"],
        "tachi-dori": ["太刀取り", "太刀取"], "jo-dori": ["杖取り", "杖取"],
        "tanto-dori": ["短刀取り", "短刀取"],
    },
}


def _norm(s: str) -> str:
    """Fold and strip everything but a-z0-9 for tolerant substring matching."""
    return re.sub(r"[^a-z0-9]", "", fold(s))


# precompute variant -> (slot, canonical), longest variants first so specific wins
_INDEX: list[tuple[str, str, str]] = []
for _slot, _table in _SLOTS.items():
    for _canon, _variants in _table.items():
        for _v in [_canon, *_variants]:
            _INDEX.append((_norm(_v), _slot, _canon))
_INDEX.sort(key=lambda t: -len(t[0]))

# kanji variant -> (slot, canonical), matched against the RAW (un-folded) text
_KANJI_INDEX: list[tuple[str, str, str]] = []
for _slot, _table in KANJI.items():
    for _canon, _variants in _table.items():
        for _v in _variants:
            _KANJI_INDEX.append((_v, _slot, _canon))
_KANJI_INDEX.sort(key=lambda t: -len(t[0]))


def classify(text: str) -> dict[str, list[str]]:
    """Which slot tokens appear in the text, matching both romaji (folded) and
    kanji (raw). Matches are consumed so a longer token (ushiro-ryote-dori /
    後ろ両手取り) is not double-counted as ryote-dori / 両手取り."""
    found: dict[str, list[str]] = {"technique": [], "attack": [], "direction": [], "form": []}
    raw = re.sub(r"\s+", "", text)                    # OCR spaces out kanji: 第 三 教 -> 第三教
    for needle, slot, canon in _KANJI_INDEX:          # kanji pass on raw text
        if needle in raw and canon not in found[slot]:
            found[slot].append(canon)
            raw = raw.replace(needle, "·")
    hay = _norm(text)
    for needle, slot, canon in _INDEX:                # romaji pass on folded text
        if needle and needle in hay and canon not in found[slot]:
            found[slot].append(canon)
            hay = hay.replace(needle, "·")
    return found


# English function/prose words that do not occur in a romaji technique title.
# Their presence marks a line as explanatory prose or a cross-reference, not a title.
_PROSE_WORDS = {
    "the", "a", "an", "and", "or", "of", "is", "are", "was", "were", "as", "to", "in",
    "on", "at", "with", "for", "this", "that", "these", "those", "you", "your", "his",
    "her", "its", "it", "he", "she", "they", "we", "because", "have", "has", "had",
    "will", "would", "can", "could", "when", "while", "then", "than", "from", "by",
    "but", "so", "if", "refer", "page", "see", "exercise", "explained", "consistently",
    "receive", "opponent", "there", "here", "which", "who", "what", "how", "why",
    "into", "about", "also", "been", "being", "one", "two", "techniques", "technique",
    "through", "again",
}
_WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")
# Japanese particles / sentence markers that occur in prose, not in short titles.
_JP_PROSE = ("は", "を", "が", "ます", "です", "から", "ので", "ため", "について", "により",
             "説明", "次の", "参照", "ました", "である", "します", "して", "など", "という")


def _looks_like_prose(line: str) -> bool:
    """Reject sentence-shaped lines and cross-references in either language."""
    if "refer" in line.lower():
        return True
    words = _WORD.findall(line)
    if len(words) > 7 or {w.lower() for w in words} & _PROSE_WORDS:
        return True
    despaced = re.sub(r"\s+", "", line)               # OCR spaces out kanji
    if any(p in despaced for p in _JP_PROSE):
        return True
    cjk = sum(1 for c in despaced if "぀" <= c <= "ヿ" or "一" <= c <= "鿿")
    return cjk > 18  # a long run of Japanese is a sentence, not a title


def is_caption(line: str) -> bool:
    """A line is a technique caption if it names a technique or attack and is not
    sentence-shaped prose."""
    if _looks_like_prose(line):
        return False
    c = classify(line)
    return bool(c["technique"] or c["attack"])


@dataclass
class Caption:
    name_romaji: str
    qualifiers: list[str] = field(default_factory=list)
    slots: dict = field(default_factory=dict)
    name_native: str | None = None
    raw: str = ""

    def slug(self) -> str:
        base = slugify(" ".join([self.name_romaji, *self.qualifiers]))
        if base:
            return base
        # kanji-only caption: build the slug from the recognized slots
        parts = [self.slots.get("attack"), self.slots.get("technique"), self.slots.get("direction")]
        parts += self.slots.get("form") or []
        return slugify("-".join(p for p in parts if p)) or "technique"


def parse_caption(romaji: str, native: str | None = None) -> Caption:
    """Parse a romaji caption like 'Kokyu Nage (Tachi dori) (Tsuki)' into slots."""
    quals = re.findall(r"\(([^)]*)\)", romaji)
    base = re.sub(r"\([^)]*\)", "", romaji).strip(" -.,")
    whole = classify(romaji)  # classify over the whole caption (base + qualifiers)
    slots = {
        "technique": whole["technique"][0] if whole["technique"] else None,
        "attack": whole["attack"][0] if whole["attack"] else None,
        "direction": whole["direction"][0] if whole["direction"] else None,
        "form": whole["form"],
    }
    return Caption(name_romaji=base, qualifiers=[q.strip() for q in quals if q.strip()],
                   slots=slots, name_native=native, raw=romaji)


def find_caption_lines(lines: list[str]) -> list[str]:
    return [ln for ln in lines if is_caption(ln)]


# -- weapon (ken / jo) captions -------------------------------------------------
# In a weapon section a caption names a suburi / awase / kata movement, not a paired
# attack. We detect these structurally (a movement word or a number marker) and parse
# them WITHOUT the taijutsu lexicon, so a jo 突き is never recorded as attack=tsuki.
_WEAPON_KANJI = ("素振り", "合わせ", "合せ", "突き", "打ち込み", "打ち", "返し", "流し",
                 "巻き", "払い", "受け", "張り", "切り", "斬り", "段")
_WEAPON_ROMAJI = ("suburi", "awase", "tsuki", "uchikomi", "uchi", "kaeshi", "nagashi",
                  "tsuburi", "kata")
_SECTION_HEADER = re.compile(r"の\s*部")          # 〇〇の部 = a group header, not a movement
_NUM_MARK = re.compile(r"[(\[（【]\s*(\d{1,2})\s*[)\]）】]")
_KANJI_RUN = re.compile(r"[぀-ヿ㐀-鿿々]+")


def is_section_header(line: str) -> bool:
    """A short '〇〇の部' line is a group header (sets sub-context), not a record."""
    despaced = re.sub(r"\s+", "", line)
    return bool(_SECTION_HEADER.search(despaced)) and len(despaced) <= 10


def is_weapon_caption(line: str) -> bool:
    if is_section_header(line) or _looks_like_prose(line):
        return False
    despaced = re.sub(r"\s+", "", line)
    has_word = any(w in despaced for w in _WEAPON_KANJI) or \
        any(w in _norm(line) for w in _WEAPON_ROMAJI)
    return bool(has_word or _NUM_MARK.search(line))


def parse_weapon_caption(line: str) -> Caption:
    """Parse a weapon-movement caption: keep the Japanese name + number, no attack/technique."""
    num = _NUM_MARK.search(line)
    quals = [num.group(1)] if num else []
    kanji = _KANJI_RUN.findall(re.sub(r"\s+", "", line))
    native = max(kanji, key=len) if kanji else None
    romaji = "" if _looks_like_kanji_only(line) else re.sub(r"\s+", " ", line).strip(" -.,")
    return Caption(name_romaji=romaji, qualifiers=quals,
                   slots={"technique": None, "attack": None, "direction": None, "form": []},
                   name_native=native, raw=re.sub(r"\s+", " ", line).strip())


def _looks_like_kanji_only(line: str) -> bool:
    return not re.search(r"[A-Za-z]", line)


def _has_ascii(s: str) -> bool:
    return bool(re.search(r"[A-Za-z]", s or ""))


def _slots_compatible(a: dict, b: dict) -> bool:
    """No slot holds two different non-null values, and they share a technique or attack."""
    for k in ("technique", "attack", "direction"):
        va, vb = a.get(k), b.get(k)
        if va and vb and va != vb:
            return False
    return bool((a.get("technique") and a.get("technique") == b.get("technique")) or
                (a.get("attack") and a.get("attack") == b.get("attack")))


def merge_bilingual(caps: list[tuple[Caption, int]]) -> list[tuple[Caption, int]]:
    """Merge a romaji caption and a kanji caption for the same technique on one page
    into a single record (keep the romaji name + the kanji as native, union the
    richer slots). Only pairs an ascii-named with a kanji-named caption, so two
    distinct romaji titles (or omote vs ura) stay separate."""
    merged: list[list] = []  # [Caption, y]
    for cap, y in caps:
        for entry in merged:
            m = entry[0]
            if (_has_ascii(cap.name_romaji) ^ _has_ascii(m.name_romaji)) and _slots_compatible(m.slots, cap.slots):
                ascii_one, kanji_one = (cap, m) if _has_ascii(cap.name_romaji) else (m, cap)
                m.name_romaji = ascii_one.name_romaji
                m.name_native = m.name_native or kanji_one.name_native or kanji_one.name_romaji
                for k in ("technique", "attack", "direction"):
                    m.slots[k] = m.slots.get(k) or cap.slots.get(k)
                form = m.slots.get("form") or []
                for f in cap.slots.get("form") or []:
                    if f not in form:
                        form.append(f)
                m.slots["form"] = form
                for q in cap.qualifiers:
                    if q not in m.qualifiers:
                        m.qualifiers.append(q)
                entry[1] = min(entry[1], y)
                break
        else:
            merged.append([cap, y])
    return [(c, y) for c, y in merged]
