"""Arabic legal-text normalisation.

Responses and rubric patterns both pass through here, so the checks can be
written once and still match the many surface forms of the same fact:
  * alef/hamza variants, alef maqsura, ta marbuta, diacritics, tatweel
  * Arabic-Indic digits and thousands separators
  * PDF extraction artifacts (letter-spaced words, object-replacement chars)
  * article numbers written as ordinals: "المادة الثالثة والسبعون بعد المائة" -> "الماده 173"
  * "المادة (53)" -> "الماده 53", "م / 44" -> "م/44"
"""
from __future__ import annotations

import re
import unicodedata

_TASHKEEL = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭ]")
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_AR = "ء-ي"
_SPACED = re.compile(rf"(?<![{_AR}])(?:[{_AR}] ){{2,}}[{_AR}](?![{_AR}])")

UNITS = {"الاولي": 1, "الحاديه": 1, "الثانيه": 2, "الثالثه": 3, "الرابعه": 4, "الخامسه": 5,
         "السادسه": 6, "السابعه": 7, "الثامنه": 8, "التاسعه": 9, "العاشره": 10}
TENS = {}
for _w, _v in [("العشر", 20), ("الثلاث", 30), ("الاربع", 40), ("الخمس", 50),
               ("الست", 60), ("السبع", 70), ("الثمان", 80), ("التسع", 90)]:
    TENS[_w + "ون"] = _v
    TENS[_w + "ين"] = _v
HUNDREDS = {}
for _stem, _v in [("", 100), ("ثلاث", 300), ("اربع", 400), ("خمس", 500), ("ست", 600), ("سبع", 700)]:
    for _h in ("مائه", "مايه", "مئه"):
        HUNDREDS["ال" + _stem + _h] = _v
for _h in ("مائتين", "مايتين", "مئتين", "مائتان", "مئتان"):
    HUNDREDS["ال" + _h] = 200


def _light(text: str) -> str:
    """Orthographic folding shared by responses and rubric patterns."""
    t = _TASHKEEL.sub("", text).replace("ـ", "")
    t = re.sub("[إأآٱ]", "ا", t)
    return t.replace("ى", "ي").replace("ة", "ه")


def normalize_pattern(pattern: str) -> str:
    return _light(pattern)


def _parse_ordinal(tail: str):
    toks = list(re.finditer(r"\S+", tail[:160]))
    words = [m.group(0).strip("()«»،,.:؛-") for m in toks]
    w = lambda k: words[k] if k < len(words) else ""
    if w(0) in UNITS:
        val, i = UNITS[w(0)], 1
        if w(1) in ("عشره", "عشر"):
            val, i = 10 + val, 2
        elif w(1).startswith("و") and w(1)[1:] in TENS:
            val, i = val + TENS[w(1)[1:]], 2
    elif w(0) in TENS:
        val, i = TENS[w(0)], 1
    elif w(0) in HUNDREDS:
        val, i = HUNDREDS[w(0)], 1
    else:
        return None
    if w(i) == "بعد" and w(i + 1) in HUNDREDS:
        val, i = val + HUNDREDS[w(i + 1)], i + 2
    last = toks[i - 1]
    return val, last.start() + len(last.group(0).rstrip("()«»،,.:؛-"))


def ordinals_to_numbers(t: str) -> str:
    out, pos = [], 0
    for m in re.finditer(r"الماده\s+", t):
        if m.start() < pos:
            continue
        parsed = _parse_ordinal(t[m.end():])
        if parsed:
            val, consumed = parsed
            out.append(t[pos:m.start()])
            out.append(f"الماده {val}")
            pos = m.end() + consumed
    out.append(t[pos:])
    return "".join(out)


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFKC", text).replace("￼", "")
    t = t.translate(_DIGITS)
    t = _light(t)
    t = t.replace("٬", ",").replace("٫", ".")
    t = re.sub(r"(?<=\d)[,،](?=\d{3}(?!\d))", "", t)          # 36,000 -> 36000
    t = _SPACED.sub(lambda m: m.group(0).replace(" ", ""), t)  # "س ب ب" -> "سبب"
    t = re.sub(r"م\s*/\s*(\d+)", r"م/\1", t)
    t = re.sub(r"(\d+)\s*/\s*(14\d\d)", r"\1/\2", t)
    t = re.sub(r"الماده\s*\(\s*(\d+)\s*\)", r"الماده \1", t)
    t = re.sub(r"[ \t ]+", " ", t)
    t = ordinals_to_numbers(t)
    return t.lower()


def arabic_ratio(text: str) -> float:
    ar = len(re.findall(f"[{_AR}]", text))
    lat = len(re.findall(r"[A-Za-z]", text))
    return ar / (ar + lat) if (ar + lat) else 0.0
