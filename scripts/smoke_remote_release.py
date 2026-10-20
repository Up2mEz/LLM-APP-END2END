"""Prove a public clean clone can fetch the pinned data and replay retrieval."""

from __future__ import annotations

import json
import argparse
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation-version", help="Also verify an existing plan; never generate model answers")
    args = parser.parse_args()
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
        plan_ids = []
        if args.evaluation_version:
            # Match the documented .env.example without copying any secret.
            plan_environment = {**environment, "NCD_MODEL": "gemma-4-E4B-it", "NCD_MAX_STEPS": "6",
                                "NCD_REQUEST_TIMEOUT": "45", "NCD_AGENT_TIMEOUT": "150"}
            result = subprocess.run(
                [sys.executable, "-B", "-m", "ncd_gemma.cli", "evaluate", "plan",
                 "--version", args.evaluation_version, "--suite", "both"],
                cwd=checkout, env=plan_environment, capture_output=True, text=True, encoding="utf-8")
            if result.returncode:
                sys.stderr.write(result.stderr)
                raise RuntimeError("Clean-clone evaluation plan verification failed")
            plan_ids = [plan["id"] for plan in json.loads(result.stdout)]
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=checkout, text=True).strip()
        manifest = json.loads((checkout / "provenance/public_data_release.json").read_text(encoding="utf-8"))
        print(json.dumps({"remote_clean_clone": "pass", "commit": commit, "evaluation_plans_verified": plan_ids,
                          "archive_sha256": manifest["archive_sha256"]}))
    finally:
        if scratch.is_relative_to(SCRATCH_ROOT):
            def remove_readonly(function, path, error):
                os.chmod(path, stat.S_IWRITE)
                function(path)

            shutil.rmtree(scratch, onerror=remove_readonly)


if __name__ == "__main__":
    main()
