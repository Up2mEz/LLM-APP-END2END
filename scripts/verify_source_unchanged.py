"""Compare the original files we used with the pre-copy hashes. No source writes."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--source", required=True, type=Path)
args = parser.parse_args()
manifest = json.loads((ROOT / "provenance/source_snapshot.json").read_text(encoding="utf-8"))
changed = []
for record in manifest["files"]:
    h = hashlib.sha256()
    path = args.source / record["source"]
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    if h.hexdigest() != record["sha256"]:
        changed.append(record["source"])
receipt = {"scope": "48 original files read by this task; not a whole-repository clean-tree claim",
           "compared": len(manifest["files"]), "changed": changed}
(ROOT / "reports/source_integrity.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps(receipt))
raise SystemExit(bool(changed))
