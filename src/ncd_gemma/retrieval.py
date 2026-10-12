from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from threading import Lock

from .config import ROOT
from .schemas import SearchArgs
from .evidence import TableContext


def file_hash(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_data():
    manifest = json.loads((ROOT / "provenance/source_snapshot.json").read_text(encoding="utf-8"))
    # The serving layer never loads gold labels or saved evaluation answers.
    for record in manifest["files"]:
        relative = record["destination"]
        if relative.startswith("data/index/") or relative == "configs/retrieval/serve_v1.json":
            path = ROOT / relative
            if not path.is_file() or file_hash(path) != record["sha256"]:
                raise ValueError(f"Missing or modified frozen retrieval artifact: {relative}")
    return file_hash(ROOT / "provenance/source_snapshot.json")


class EvidenceRetriever:
    """Use the copied Retriever unchanged, with frozen artifacts and offline weights."""
    def __init__(self):
        started = time.monotonic()
        def progress(stage):
            if os.getenv("NCD_DEBUG_STARTUP") == "1":
                print(f"retrieval startup: {stage} ({time.monotonic() - started:.1f}s)", flush=True)
        progress("verify artifacts")
        self.snapshot_hash = verify_data()
        from huggingface_hub import constants
        revision_file = Path(constants.HF_HUB_CACHE) / "models--BAAI--bge-m3/refs/main"
        expected = "5617a9f61b028005a4858fdac845db406aefb181"
        if not revision_file.is_file() or revision_file.read_text().strip() != expected:
            raise ValueError("The local bge-m3 main reference must match the frozen embedding revision; see README")
        progress("import torch")
        import torch
        torch.set_num_threads(max(1, min(8, int(os.getenv("NCD_CPU_THREADS", "4")))))
        progress("load bge-m3 and index")
        from ncdqa.retrieval.search import Retriever
        self.raw = Retriever(ROOT / "configs/retrieval/serve_v1.json", device="cpu")
        table_path = ROOT / 'data/table_context/tables.jsonl'
        tables = [json.loads(s) for s in table_path.read_text(encoding='utf-8').splitlines()] if table_path.is_file() else []
        self.table_context = TableContext(self.raw.parents, tables)
        from .focus import PassageFocus
        self.focus = PassageFocus(self.raw.parents)
        from .passage_rerank import PassageReranker
        self.passage_reranker = PassageReranker()
        progress("ready")
        self.lock = Lock()
        self.allowed = {key: {str(c.get(key, "general" if key == "population" else ""))
                              for c in self.raw.parents}
                        for key in ("document_id", "primary_group", "document_type", "population")}

    def search(self, args: SearchArgs, variant: str = "B") -> list[dict]:
        filters = args.filters.model_dump(exclude_none=True)
        for key, value in filters.items():
            if value not in self.allowed[key]:
                raise ValueError(f"Unknown filter value for {key}")
        with self.lock:
            hits, raw_seen = [], set()
            for hit in self.raw.search(args.query, variant=variant, k=args.top_k, filters=filters):
                hits.append(hit)
                raw_seen.add(hit['chunk_id'])
            # For an explicit "keep X and Y separate?" question, admit a
            # frozen parent only when it literally states that pair. This
            # complements semantic search without guessing another field or
            # changing the source index.
            if 'แยก' in args.query:
                fields = [word for word in ('น้ำหนัก', 'ส่วนสูง', 'รอบเอว', 'รอบสะโพก') if word in args.query]
                fields.sort(key=args.query.index)
                if len(fields) >= 2:
                    phrase = 'แยก' + fields[0] + 'และ' + fields[1]
                    for parent in self.raw.parents:
                        if parent['chunk_id'] in raw_seen or not phrase in re.sub(r'\s+', '', parent['text']):
                            continue
                        if filters and any(str(parent.get(key, 'general' if key == 'population' else '')) != value for key,value in filters.items()):
                            continue
                        hits.append({**parent, 'score': 0.0, 'lexical_exact': True})
                        raw_seen.add(parent['chunk_id'])
            evidence, seen = [], set()
            for hit in hits:
                for window in self.focus.select(self.table_context.enrich(hit), args.query):
                    fingerprint = (window['document_id'], window['edition_id'], window['text'])
                    if fingerprint not in seen:
                        seen.add(fingerprint)
                        evidence.append(window)
            ranked = self.passage_reranker.rank(args.query,evidence)
            return sorted(ranked, key=lambda hit: not hit.get('lexical_exact', False))
