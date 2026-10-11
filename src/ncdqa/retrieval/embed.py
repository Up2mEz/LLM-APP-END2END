"""Embedding models for dense retrieval: one place for each model's prefixes and length limit.

Prefixes and max length come from the model cards; they are recorded in every index manifest so a run can be audited.
Vectors are L2-normalized so the inner product is the cosine similarity.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class EmbeddingModel:
    key: str
    hf_id: str
    query_prefix: str
    passage_prefix: str
    max_seq_length: int


MODELS = {
    "e5-base": EmbeddingModel("e5-base", "intfloat/multilingual-e5-base", "query: ", "passage: ", 512),
    # bge-m3 takes no prefix; its own limit is 8192, capped at 512 here so both chunk sizes are comparable with e5
    "bge-m3": EmbeddingModel("bge-m3", "BAAI/bge-m3", "", "", 512),
}


def load(model: EmbeddingModel, device: str = "cpu"):
    from sentence_transformers import SentenceTransformer
    st = SentenceTransformer(model.hf_id, device=device)
    st.max_seq_length = model.max_seq_length
    return st


def encode(st, texts: list[str], prefix: str, batch_size: int = 16, show_progress: bool = False) -> np.ndarray:
    vectors = st.encode([prefix + t for t in texts], batch_size=batch_size, normalize_embeddings=True,
                        convert_to_numpy=True, show_progress_bar=show_progress)
    return vectors.astype(np.float32)
