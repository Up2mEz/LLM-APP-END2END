"""Copy an allow-listed snapshot. Read the source; write only this project.

Usage: python scripts/import_source.py --source PATH
Private corpus artifacts stay under ignored data/. No credentials are copied.
"""
import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
MODULES = ["__init__", "search", "embed", "dense", "parent_child", "fusion", "bm25", "thai_tokens", "evaluate", "answer_match"]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    if source == PROJECT or source.is_relative_to(PROJECT) or PROJECT.is_relative_to(source):
        raise SystemExit("Source and destination must be separate directories")
    files = [(f"src/ncdqa/retrieval/{m}.py", f"src/ncdqa/retrieval/{m}.py") for m in MODULES]
    files += [("src/ncdqa/__init__.py", "src/ncdqa/__init__.py")]
    files += [(f"configs/retrieval/{f}.json", f"configs/retrieval/{f}.json") for f in ("serve_v1", "frozen_v1")]
    for size in (128, 512):
        for name in ("chunks.jsonl", "chunk_stats.json"):
            rel = f"data/index/chunks-v12-t{size}/{name}"
            files.append((rel, rel))
    for name in ("vectors.npy", "chunk_ids.json", "index_manifest.json"):
        rel = f"data/index/dense-bge-m3-t128-v12/{name}"
        files.append((rel, rel))
    files += [("data/handoff/track_c_20261012/questions_all_reviewed.jsonl", "data/gold/questions_all_reviewed.jsonl"),
              ("data/manifests/corpus_normalized-v12_inventory.json", "data/manifests/corpus_normalized-v12_inventory.json")]
    for split in ("dev", "test"):
        for variant in ("A", "B", "C"):
            for filename in ("results.jsonl", "metrics.json", "run_manifest.json", "config.json"):
                rel = f"data/index/runs/final/{split}-{variant}-bge-m3/{filename}"
                files.append((rel, f"data/frozen/{split}-{variant}/{filename}"))
    for filename in ("question.schema.json", "retrieval_result.schema.json"):
        files.append((f"data/schemas/rag/{filename}", f"schemas/{filename}"))
    missing = [rel for rel, _ in files if not (source / rel).is_file()]
    if missing:
        raise SystemExit("Missing source files: " + ", ".join(missing))
    copied = []
    for rel, dest_rel in files:
        src, dest = source / rel, PROJECT / dest_rel
        digest = sha(src)
        if dest.exists() and sha(dest) != digest:
            raise SystemExit(f"Refusing to overwrite changed destination: {dest_rel}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copyfile(src, dest)
        if sha(dest) != digest or sha(src) != digest:
            raise SystemExit(f"Copy integrity failed: {rel}")
        copied.append({"source": rel, "destination": dest_rel, "sha256": digest})
    provenance = {"source_repository": "https://github.com/Chaiporn2005/thai-ncd-guideline-qa",
                  "source_commit_reviewed": "3fb287cdbceab04d13e73f6dfb3bdf5eeb1b6829",
                  "copied_at_utc": datetime.now(timezone.utc).isoformat(),
                  "source_working_tree_clean": "not_assumed", "files": copied,
                  "rights": "Corpus stays private. Publishing requires a separately cleared corpus or authorized access."}
    (PROJECT / "provenance").mkdir(exist_ok=True)
    (PROJECT / "provenance/source_snapshot.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"copied_and_hash_verified": len(copied), "source_mutations": 0}))


if __name__ == "__main__":
    main()
