"""`search(query, variant, k, filters)`: the retrieval interface for the evaluation harness (Track C) and the answer step (Track D).

The settings are those of `configs/retrieval/frozen_v1.json`, written machine-readably in `configs/retrieval/serve_v1.json`:
  variant "A"  dense, parent-child (128-token children matched with bge-m3, 512-token parents returned)
  variant "B"  A fused with Thai BM25 (char3, k1 2.18, b 0.86) by a convex combination of min-max scores, alpha 0.6   <- default
  variant "C"  B, then the top-30 re-scored by the cross-encoder BAAI/bge-reranker-v2-m3 (slow on CPU: 15-36 s per query; use a GPU)
Each hit carries what an answer step and a citation need: chunk id, score, document and edition, page range, section path, the
verbatim text, document type, disease group, population tag, page statuses and the injection flags found in the text.
`filters` keeps only hits whose metadata match (document_id, primary_group, document_type, population: a value or a list); the filter
is applied to the 100 fused candidates before the top-k is cut, so a filter never returns fewer hits than exist.

    from ncdqa.retrieval.search import Retriever
    r = Retriever()                       # loads the model, the index and BM25 once (about 20 s on CPU)
    hits = r.search("ค่า HbA1c เป้าหมายในผู้ป่วยเบาหวานคือเท่าไร", variant="B", k=5)
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = ROOT / "configs/retrieval/serve_v1.json"


def _read(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").split("\n") if x.strip()]


class Retriever:
    def __init__(self, config: Path = DEFAULT_CONFIG, device: str = "cpu"):
        from . import embed
        from .bm25 import BM25Index, tokenize_units
        from .dense import DenseIndex
        from .parent_child import ParentChildIndex, build_parent_map

        cfg = json.loads(config.read_text(encoding="utf-8"))
        self.cfg = cfg
        paths = {k: (ROOT / v) for k, v in cfg["paths"].items()}
        self.model = embed.MODELS[cfg["model"]]
        self.st = embed.load(self.model, device)
        self.parents = _read(paths["parent_chunks"] / "chunks.jsonl")
        self.units = {c["chunk_id"]: c for c in self.parents}
        children = _read(paths["child_chunks"] / "chunks.jsonl")
        self.pc = ParentChildIndex(DenseIndex.load(paths["dense_index"]), build_parent_map(children, self.parents))
        lex = cfg["lexical"]
        self.tokenizer = lex["tokenizer"]
        self.bm25 = BM25Index([c["chunk_id"] for c in self.parents], tokenize_units(self.parents, self.tokenizer, (), True), lex["k1"], lex["b"])
        self.pool, self.alpha = cfg["fusion"]["pool"], cfg["fusion"]["alpha"]
        self._reranker = None
        self._embed = embed

    def _candidates(self, query: str, depth: int) -> list[tuple[str, float]]:
        from . import fusion
        from .thai_tokens import tokenize
        qvec = self._embed.encode(self.st, [query], self.model.query_prefix)
        dense = [(p, s) for p, s, _ in self.pc.search(qvec, self.pool, self.pool * 4)[0]]
        lexical = self.bm25.top(tokenize(query, self.tokenizer, ()), self.pool)
        return fusion.convex(dense, lexical, self.alpha, depth) if lexical else dense[:depth]

    def _hit(self, rank: int, chunk_id: str, score: float) -> dict:
        c = self.units[chunk_id]
        return {"rank": rank, "chunk_id": chunk_id, "score": round(float(score), 5), "document_id": c["document_id"], "edition_id": c["edition_id"],
                "pdf_page_start": c["pdf_page_start"], "pdf_page_end": c["pdf_page_end"], "section_path": c["section_path"], "text": c["text"],
                "header_text": c["header_text"], "document_type": c["document_type"], "primary_group": c["primary_group"],
                "population": c.get("population", "general"), "source_page_statuses": c["source_page_statuses"],
                "injection_flags": c["injection_flags"], "char_start": c["char_start"], "char_end": c["char_end"]}

    def search(self, query: str, variant: str = "B", k: int = 10, filters: dict | None = None) -> list[dict]:
        if variant not in ("A", "B", "C"):
            raise ValueError("variant must be A, B or C")
        depth = max(self.cfg["rerank"]["depth"], k) if variant == "C" else max(k, self.pool if filters else k)
        if variant == "A":
            from . import embed  # noqa: F401
            qvec = self._embed.encode(self.st, [query], self.model.query_prefix)
            ranked = [(p, s) for p, s, _ in self.pc.search(qvec, depth, self.pool * 4)[0]]
        else:
            ranked = self._candidates(query, depth)
        if variant == "C":
            ranked = self._rerank(query, ranked[:self.cfg["rerank"]["depth"]])
        if filters:
            ranked = [(u, s) for u, s in ranked if self._match(self.units[u], filters)]
        return [self._hit(i, u, s) for i, (u, s) in enumerate(ranked[:k], 1)]

    @staticmethod
    def _match(chunk: dict, filters: dict) -> bool:
        for key, want in filters.items():
            have = chunk.get(key, "general" if key == "population" else None)
            if have not in (want if isinstance(want, (list, tuple, set)) else [want]):
                return False
        return True

    def _rerank(self, query: str, ranked: list[tuple[str, float]]) -> list[tuple[str, float]]:
        if self._reranker is None:
            from sentence_transformers import CrossEncoder
            self._reranker = CrossEncoder(self.cfg["rerank"]["model"], max_length=512)
        pairs = [(query, (self.units[u]["header_text"] + "\n" if self.units[u]["header_text"] else "") + self.units[u]["text"]) for u, _ in ranked]
        scores = self._reranker.predict(pairs, batch_size=8, show_progress_bar=False)
        return sorted(((u, float(s)) for (u, _), s in zip(ranked, scores)), key=lambda x: -x[1])
