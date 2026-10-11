"""Fusing a dense ranking with a lexical ranking: Reciprocal Rank Fusion and convex combination (Track B).

* RRF (Cormack, Clarke & Buettcher, SIGIR 2009): score(d) = sum over rankings of 1 / (k + rank(d)); the paper fixed k = 60 in a pilot
  and never changed it. Rank-only, so score scales of the two retrievers do not matter.
* Convex combination (Bruch, Gai & Ingber 2023, arXiv 2210.11934): alpha * norm(dense) + (1 - alpha) * norm(lexical) with min-max
  normalisation of each list; they report it beats RRF and that RRF is sensitive to its parameters.
A document missing from one list gets the minimum normalised score (0) from that list.
"""

from __future__ import annotations


def rrf(rankings: list[list[str]], k: int = 60, top: int = 100) -> list[tuple[str, float]]:
    score: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc in enumerate(ranking, 1):
            score[doc] = score.get(doc, 0.0) + 1.0 / (k + rank)
    return sorted(score.items(), key=lambda kv: (-kv[1], kv[0]))[:top]


def minmax(scored: list[tuple[str, float]]) -> dict[str, float]:
    if not scored:
        return {}
    values = [s for _, s in scored]
    low, high = min(values), max(values)
    span = high - low
    return {d: (s - low) / span if span > 0 else 1.0 for d, s in scored}


def convex(dense: list[tuple[str, float]], lexical: list[tuple[str, float]], alpha: float, top: int = 100) -> list[tuple[str, float]]:
    a, b = minmax(dense), minmax(lexical)
    docs = set(a) | set(b)
    fused = {d: alpha * a.get(d, 0.0) + (1 - alpha) * b.get(d, 0.0) for d in docs}
    return sorted(fused.items(), key=lambda kv: (-kv[1], kv[0]))[:top]
