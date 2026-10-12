"""Download the two public encoder weights at fixed revisions for a clean clone."""

from __future__ import annotations

import json
from pathlib import Path

from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache/hf_public/hub"
MODELS = {
    "BAAI/bge-m3": "5617a9f61b028005a4858fdac845db406aefb181",
    "BAAI/bge-reranker-v2-m3": "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e",
}


def main() -> None:
    report = {}
    for repo, revision in MODELS.items():
        path = Path(snapshot_download(repo_id=repo, revision=revision, cache_dir=CACHE))
        if path.name != revision or not path.is_dir():
            raise ValueError(f"Unexpected revision for {repo}")
        if repo == "BAAI/bge-m3":
            # The preserved source retriever loads its model by name, which
            # resolves through refs/main in offline mode. Point only this
            # project-owned cache at the frozen commit.
            main_ref = CACHE / "models--BAAI--bge-m3/refs/main"
            main_ref.parent.mkdir(parents=True, exist_ok=True)
            main_ref.write_text(revision, encoding="utf-8")
        report[repo] = revision
    print(json.dumps({"cache": str(CACHE), "revisions": report}))


if __name__ == "__main__":
    main()
