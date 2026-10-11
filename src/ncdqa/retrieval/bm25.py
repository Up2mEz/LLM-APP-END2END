"""Thai BM25 over chunk units with bm25s (Lucene-variant scoring), scoring every unit for a query (exact, ~4k-24k units)."""

from __future__ import annotations

import numpy as np
import bm25s

from .thai_tokens import tokenize


class BM25Index:
    def __init__(self, unit_ids: list[str], token_lists: list[list[str]], k1: float, b: float, method: str = "lucene"):
        self.unit_ids = unit_ids
        self.k1, self.b, self.method = k1, b, method
        self.model = bm25s.BM25(k1=k1, b=b, method=method)
        self.model.index(token_lists, show_progress=False)

    def scores(self, query_tokens: list[str]) -> np.ndarray:
        vocab = self.model.vocab_dict
        known = [t for t in query_tokens if t in vocab]
        if not known:
            return np.zeros(len(self.unit_ids), dtype=np.float32)
        return self.model.get_scores(known)

    def top(self, query_tokens: list[str], n: int = 100) -> list[tuple[str, float]]:
        s = self.scores(query_tokens)
        n = min(n, len(s))
        idx = np.argpartition(-s, n - 1)[:n]
        idx = idx[np.argsort(-s[idx])]
        return [(self.unit_ids[i], float(s[i])) for i in idx if s[i] > 0]


def unit_text(chunk: dict, with_header: bool) -> str:
    return (chunk["header_text"] + "\n" if with_header and chunk["header_text"] else "") + chunk["text"]


def tokenize_units(chunks: list[dict], mode: str, extra_words: tuple[str, ...], with_header: bool) -> list[list[str]]:
    return [tokenize(unit_text(c, with_header), mode, extra_words) for c in chunks]
