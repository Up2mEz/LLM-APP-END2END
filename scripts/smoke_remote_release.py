"""Prove a public clean clone can fetch the pinned data and replay retrieval."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRATCH_ROOT = (ROOT / "tmp").resolve()
REPOSITORY = "https://github.com/Up2mEz/LLM-APP-END2END.git"


def main() -> None:
    SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="remote-clone-", dir=SCRATCH_ROOT)).resolve()
    if not scratch.is_relative_to(SCRATCH_ROOT):
        raise ValueError("Scratch directory escaped workspace")
    try:
        checkout = scratch / "checkout"
        subprocess.run(["git", "clone", "--depth", "1", "--branch", "main", REPOSITORY, str(checkout)], check=True)
        environment = {**os.environ, "PYTHONPATH": str(checkout / "src")}
        subprocess.run([sys.executable, "-B", "scripts/public_data.py", "fetch"], cwd=checkout, env=environment, check=True)
        subprocess.run([sys.executable, "-B", "-m", "ncd_gemma.cli", "evaluate", "retrieval"],
                       cwd=checkout, env=environment, check=True)
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=checkout, text=True).strip()
        manifest = json.loads((checkout / "provenance/public_data_release.json").read_text(encoding="utf-8"))
        print(json.dumps({"remote_clean_clone": "pass", "commit": commit,
                          "archive_sha256": manifest["archive_sha256"]}))
    finally:
        if scratch.is_relative_to(SCRATCH_ROOT):
            def remove_readonly(function, path, error):
                os.chmod(path, stat.S_IWRITE)
                function(path)

            shutil.rmtree(scratch, onerror=remove_readonly)


if __name__ == "__main__":
    main()
