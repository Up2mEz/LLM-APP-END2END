"""Exact dense search over normalized chunk vectors (brute-force inner product; no ANN needed at this size)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


class DenseIndex:
    def __init__(self, vectors: np.ndarray, chunk_ids: list[str]):
        if vectors.shape[0] != len(chunk_ids):
            raise ValueError("one vector per chunk id is required")
        self.vectors, self.chunk_ids = vectors, chunk_ids

    def search(self, query_vectors: np.ndarray, k: int) -> list[list[tuple[str, float]]]:
        scores = query_vectors @ self.vectors.T
        k = min(k, scores.shape[1])
        top = np.argpartition(-scores, k - 1, axis=1)[:, :k]
        out = []
        for row, idx in enumerate(top):
            idx = idx[np.argsort(-scores[row, idx])]
            out.append([(self.chunk_ids[i], float(scores[row, i])) for i in idx])
        return out

    def save(self, folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        np.save(folder / "vectors.npy", self.vectors)
        (folder / "chunk_ids.json").write_text(json.dumps(self.chunk_ids), encoding="utf-8")

    @classmethod
    def load(cls, folder: Path) -> "DenseIndex":
        return cls(np.load(folder / "vectors.npy"), json.loads((folder / "chunk_ids.json").read_text(encoding="utf-8")))
