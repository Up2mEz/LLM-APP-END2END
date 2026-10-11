"""Tokenizers for Thai BM25 (Track B): default newmm, Latin-aware newmm, newmm with a corpus-learned dictionary, character n-grams.

Why several: the default PyThaiNLP dictionary splits medical vocabulary badly ("HbA1c" -> "HbA", "1", "c"; a loan-word drug name into
fragments), so the lexical side of hybrid retrieval cannot match it. Which fix helps is measured, not assumed.

modes
  newmm        PyThaiNLP newmm with its default dictionary (baseline)
  newmm_latin  Latin/digit runs (HbA1c, eGFR, LDL-C, mg/dL) are kept whole and lower-cased; Thai runs go to newmm
  newmm_dict   as newmm_latin, with a learned list of extra Thai words added to the dictionary
  char3/char4  character n-grams over Thai runs (no dictionary at all); Latin runs as in newmm_latin
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from pythainlp.corpus import thai_words
from pythainlp.tokenize import word_tokenize
from pythainlp.util import Trie

LATIN_RUN = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-_/.%]*[A-Za-z0-9%]|[A-Za-z0-9]")
THAI_RUN = re.compile(r"[฀-๿]+")
KEEP = re.compile(r"[฀-๿A-Za-z0-9]")


def load_dictionary(path: Path | None) -> list[str]:
    """One word per line; `#` lines and columns after a tab are ignored (the learner writes df/provenance after the tab)."""
    if path is None:
        return []
    words = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            words.append(line.split("\t")[0].strip())
    return words


@lru_cache(maxsize=4)
def _trie(extra: tuple[str, ...]) -> Trie:
    return Trie(list(thai_words()) + list(extra))


def _segments(text: str):
    """Yield (kind, string) for alternating Thai and Latin/digit runs."""
    pos = 0
    for m in re.finditer(r"([฀-๿]+)|([A-Za-z0-9][^\s฀-๿]*)", text):
        if m.group(1):
            yield "th", m.group(1)
        else:
            yield "la", m.group(2)
        pos = m.end()


def tokenize(text: str, mode: str = "newmm", extra_words: tuple[str, ...] = ()) -> list[str]:
    if mode == "newmm":
        return [t for t in word_tokenize(text, engine="newmm", keep_whitespace=False) if KEEP.search(t)]
    out: list[str] = []
    trie = _trie(extra_words) if mode == "newmm_dict" else None
    for kind, segment in _segments(text):
        if kind == "la":
            for m in LATIN_RUN.finditer(segment):
                out.append(m.group(0).lower().strip(".-_/"))
            continue
        if mode in ("newmm_latin", "newmm_dict"):
            tokens = word_tokenize(segment, engine="newmm", custom_dict=trie, keep_whitespace=False) if trie else \
                word_tokenize(segment, engine="newmm", keep_whitespace=False)
            out.extend(t for t in tokens if KEEP.search(t))
        elif mode in ("char3", "char4"):
            n = int(mode[-1])
            out.extend(segment[i:i + n] for i in range(max(len(segment) - n + 1, 1)))
        else:
            raise ValueError(f"unknown tokenizer mode {mode!r}")
    return [t for t in out if t]
