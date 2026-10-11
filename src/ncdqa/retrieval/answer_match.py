"""Answer-containment matching for numeric answers (Track B, lenient relevance).

A question has one evidence page, but the same fact is often stated in other documents, and the retriever is scored a
miss when it returns one of them. This module recognises such a unit without extra labels: the unit counts as holding the
answer when it contains every strong number of the gold answer (with its unit, after unit spelling is normalised) and
shares enough wording with the question.

It only works for answers with numbers (about a third of the questions). Free-text answers have no anchor here, so they
are scored by the evidence / alt_evidence rule only. The match is deliberately conservative: a unit that merely contains
"5" is not a match.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")

# spelling variants of the same unit; applied to text with whitespace already removed, longest first
_UNIT_RULES: list[tuple[str, str]] = [
    (r"มิลลิกรัมต่อเดซิลิตร|มิลลิกรัม/เดซิลิตร|มก\./?ดล\.?|มก/ดล|mg/dl", "mg/dl"),
    (r"นาโนกรัมต่อมิลลิลิตร|นาโนกรัม/มิลลิลิตร|ng/ml", "ng/ml"),
    (r"มิลลิเมตรปรอท|mmhg", "mmhg"),
    (r"ร้อยละ(\d+(?:\.\d+)?)", r"\1%"),
    (r"เปอร์เซ็นต์|เปอร์เซนต์", "%"),
    (r"กิโลกรัม|กก\.", "kg"),
    (r"มิลลิกรัม|มก\.", "mg"),
    (r"มิลลิลิตร|มล\.", "ml"),
    (r"เซนติเมตร|ซม\.", "cm"),
]
_UNIT_RE = [(re.compile(p, re.I), r) for p, r in _UNIT_RULES]
_DASH = re.compile(r"[–—‑~]")
_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")
_SPACE = re.compile(r"[\s​]+")
_NUMBER = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)(?!\d)")
_UNIT_AFTER = re.compile(r"^(%|mg/dl|ng/ml|mmhg|mg|kg|ml|cm|g|นาที|ชั่วโมง|สัปดาห์|เดือน|ปี|วัน|ครั้ง|รอบ|ชม\.?)")
_MAX_GAP = 12  # characters allowed between a number and its unit


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text).translate(_THAI_DIGITS)
    text = _SPACE.sub("", text)
    text = _DASH.sub("-", text)
    text = _THOUSANDS.sub("", text)
    for pattern, repl in _UNIT_RE:
        text = pattern.sub(repl, text)
    return text.lower()


@dataclass(frozen=True)
class Anchor:
    number: str
    unit: str | None


def anchors(answer: str | None, limit: int = 4) -> list[Anchor]:
    """Strong numbers of an answer: two or more digits, a decimal, or a number with a unit. [] when there are none."""
    if not answer:
        return []
    text = normalize(answer)
    found: list[Anchor] = []
    for m in _NUMBER.finditer(text):
        number = m.group(1)
        unit_match = _UNIT_AFTER.match(text[m.end():m.end() + 6])
        unit = unit_match.group(1) if unit_match else None
        year_like = len(number) == 4 and number.startswith("25")
        if (len(number) >= 2 or "." in number or unit) and not year_like:
            found.append(Anchor(number, unit))
    return found[:limit]


def _has_anchor(text: str, anchor: Anchor) -> bool:
    for m in re.finditer(rf"(?<![\d.]){re.escape(anchor.number)}(?!\d)", text):
        if anchor.unit is None:
            return True
        window = text[m.end():m.end() + _MAX_GAP + len(anchor.unit)]
        if anchor.unit in window:
            return True
    return False


def _grams(text: str, n: int = 4) -> set[str]:
    return {text[i:i + n] for i in range(max(0, len(text) - n + 1))}


class AnswerMatcher:
    """Matches a unit to a question's numeric answer. Wording overlap with the question is weighted by how rare each
    4-character piece is across the corpus pages (idf), so common words ("ผู้ป่วย", "เบาหวาน") do not count.

    Calibrated on the 141 silver questions at page level: the gold page scores a median 0.27 while other pages that merely
    hold the same number score a median 0.06; at 0.35 only 7 of 2,879 such pages pass (those spot-checked state the same
    fact), at 0.22-0.30 roughly half are unrelated. The default 0.35 is therefore a conservative lower bound.
    """

    def __init__(self, page_texts: list[str], min_overlap: float = 0.35):
        import math
        from collections import Counter
        df: Counter = Counter()
        for text in page_texts:
            df.update(_grams(normalize(text)))
        n = len(page_texts)
        self._idf = lambda g, _df=df, _n=n, _log=math.log: _log((_n + 1) / (_df.get(g, 0) + 1))
        self.min_overlap = min_overlap

    def overlap(self, question: str, normalized_text: str) -> float:
        grams = _grams(normalize(question))
        total = sum(self._idf(g) for g in grams)
        if not total:
            return 0.0
        return sum(self._idf(g) for g in grams & _grams(normalized_text)) / total

    def matches(self, answer: str | None, question: str, unit_text: str) -> bool:
        wanted = anchors(answer)
        if not wanted:
            return False
        text = normalize(unit_text)
        return all(_has_anchor(text, a) for a in wanted) and self.overlap(question, text) >= self.min_overlap
