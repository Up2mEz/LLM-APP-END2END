"""Record completed local checks; never turn an unrun check into a pass."""
import importlib.metadata
import json
import platform
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
suite = ET.parse(ROOT / "private/tests-final.xml").getroot().find("testsuite")
if suite is None:
    raise SystemExit("No completed pytest result")
tests = {key: int(suite.attrib[key]) for key in ("tests", "failures", "errors", "skipped")}
tests["seconds"] = float(suite.attrib["time"])
source = json.loads((ROOT / "reports/source_integrity.json").read_text())
retrieval = json.loads((ROOT / "reports/retrieval_metrics.json").read_text())
doctor = json.loads((ROOT / "reports/doctor-retrieval.json").read_text())
probe_path = ROOT / "reports/doctor-proxy.json"
if not probe_path.exists():
    probe_path = ROOT / "reports/doctor.json"
probe = json.loads(probe_path.read_text()).get("proxy_probe", {})
report = {
    "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "python": platform.python_version(),
    "tests": tests,
    "tests_passed": tests["tests"] - tests["failures"] - tests["errors"] - tests["skipped"],
    "pytest_passed": tests["failures"] == tests["errors"] == 0,
    "source_file_hash_check": source,
    "frozen_runs_verified": len(retrieval["runs"]),
    "actual_retrieval_probe": doctor.get("retrieval"),
    "actual_proxy_native_tool_probe": probe,
    "scope": "Unit/API tests use fake model and retriever. Real retrieval and proxy probes are separate checks, not end-to-end answer evaluation.",
}
(ROOT / "reports/validation.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
versions = sorted({f"{d.metadata['Name']}=={d.version}" for d in importlib.metadata.distributions()
                   if d.metadata.get("Name") and d.metadata["Name"].lower() != "ncd-gemma"}, key=str.casefold)
(ROOT / "requirements-lock.txt").write_text(
    "# Observed Windows / Python " + platform.python_version() + " environment; generated from installed metadata.\n"
    + "\n".join(versions) + "\n-e .[dev]\n", encoding="utf-8")
print(json.dumps({"tests": tests, "source_files_unchanged": not source["changed"], "locked_packages": len(versions)}))
