"""Parent-child (small-to-big) retrieval: match with small chunks, hand back the larger chunk that contains them.

Small chunks give sharper embeddings (one fact per vector); the larger parent gives the generator, and the relevance
rule, the surrounding context (table header, condition, the sentence before). The parent of a child is the parent chunk
of the same document whose span `(pdf_page, char)` holds the child's start. Both sets come from the same chunker, so a
child can straddle two parents; it then belongs to the parent holding its start, and that is recorded in the map.
"""

from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict

import numpy as np

from .dense import DenseIndex


def build_parent_map(children: list[dict], parents: list[dict]) -> dict[str, str]:
    by_doc: dict[str, list[dict]] = defaultdict(list)
    for p in parents:
        by_doc[p["document_id"]].append(p)
    starts: dict[str, list[tuple]] = {}
    for doc, items in by_doc.items():
        items.sort(key=lambda p: (p["pdf_page_start"], p["char_start"]))
        starts[doc] = [(p["pdf_page_start"], p["char_start"]) for p in items]
    mapping: dict[str, str] = {}
    for child in children:
        doc = child["document_id"]
        if doc not in by_doc:
            continue
        pos = (child["pdf_page_start"], child["char_start"])
        at = max(bisect_right(starts[doc], pos) - 1, 0)
        candidate = by_doc[doc][at]
        end = (candidate["pdf_page_end"], candidate["char_end"])
        if pos > end and at + 1 < len(by_doc[doc]):  # the start fell in the gap between two parents: take the next one
            candidate = by_doc[doc][at + 1]
        mapping[child["chunk_id"]] = candidate["chunk_id"]
    return mapping


class ParentChildIndex:
    """Dense search over child vectors, returning parents (best child score, parents de-duplicated in rank order)."""

    def __init__(self, child_index: DenseIndex, parent_of: dict[str, str]):
        self.child_index, self.parent_of = child_index, parent_of

    def search(self, query_vectors: np.ndarray, k: int, fetch: int = 50) -> list[list[tuple[str, float, str]]]:
        """Per query: up to k `(parent_id, best_child_score, best_child_id)`."""
        out = []
        for hits in self.child_index.search(query_vectors, fetch):
            seen: dict[str, tuple[float, str]] = {}
            for child_id, score in hits:
                parent = self.parent_of.get(child_id)
                if parent is not None and parent not in seen:
                    seen[parent] = (score, child_id)
            out.append([(p, s, c) for p, (s, c) in list(seen.items())[:k]])
        return out
