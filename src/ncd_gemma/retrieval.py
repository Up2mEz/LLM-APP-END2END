from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from threading import Lock

from .config import ROOT
from .schemas import SearchArgs


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
            return self.raw.search(args.query, variant=variant, k=args.top_k, filters=filters)
