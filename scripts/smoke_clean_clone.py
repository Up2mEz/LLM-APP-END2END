"""Rehearse a clean checkout using the release bundle without touching live data."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRATCH_ROOT = (ROOT / "tmp").resolve()


def main() -> None:
    archive = ROOT / "output/public_data/ncd-data-v12.zip"
    if not archive.is_file():
        raise ValueError("Run scripts/public_data.py package first")
    SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="clean-clone-", dir=SCRATCH_ROOT)).resolve()
    if not scratch.is_relative_to(SCRATCH_ROOT):
        raise ValueError("Scratch directory escaped workspace")
    try:
        shutil.copytree(ROOT / "src", scratch / "src")
        shutil.copytree(ROOT / "configs", scratch / "configs")
        (scratch / "scripts").mkdir()
        shutil.copy2(ROOT / "scripts/public_data.py", scratch / "scripts/public_data.py")
        (scratch / "provenance").mkdir()
        shutil.copy2(ROOT / "provenance/source_snapshot.json", scratch / "provenance/source_snapshot.json")
        manifest = json.loads((ROOT / "provenance/public_data_release.json").read_text(encoding="utf-8"))
        manifest["asset_url"] = archive.as_uri()
        (scratch / "provenance/public_data_release.json").write_text(json.dumps(manifest), encoding="utf-8")
        environment = {**os.environ, "PYTHONPATH": str(scratch / "src")}
        for command in (
            [sys.executable, "-B", "scripts/public_data.py", "fetch"],
            [sys.executable, "-B", "-m", "ncd_gemma.cli", "evaluate", "retrieval"],
        ):
            subprocess.run(command, cwd=scratch, env=environment, check=True)
        print(json.dumps({"clean_clone": "pass", "archive_sha256": manifest["archive_sha256"]}))
    finally:
        if scratch.is_relative_to(SCRATCH_ROOT):
            shutil.rmtree(scratch)


if __name__ == "__main__":
    main()
