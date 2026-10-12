"""Package the exact local retrieval/evaluation snapshot for a GitHub release.

The archive contains extracted text/index and gold, not source PDFs, credentials,
model weights, private run answers, or raw LLM cache.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PROVENANCE = ROOT / "provenance/source_snapshot.json"
MANIFEST = ROOT / "provenance/public_data_release.json"
ARCHIVE = ROOT / "output/public_data/ncd-data-v12.zip"
CATEGORIES = {"index", "gold", "frozen", "manifests", "table_context"}
ASSET_URL = "https://github.com/Up2mEz/LLM-APP-END2END/releases/download/data-v12/ncd-data-v12.zip"


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def selected_files() -> list[Path]:
    files = sorted(path for path in DATA.rglob("*") if path.is_file() and path.relative_to(DATA).parts[0] in CATEGORIES)
    if not files or {path.relative_to(DATA).parts[0] for path in files} != CATEGORIES:
        raise ValueError("Public data snapshot is incomplete")
    return files


def package() -> dict:
    source = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    frozen_hashes = {record["destination"]: record["sha256"] for record in source["files"]}
    files = selected_files()
    records = []
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        sha = digest(path)
        if relative in frozen_hashes and sha != frozen_hashes[relative]:
            raise ValueError(f"Snapshot changed: {relative}")
        records.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha})
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as bundle:
        for record in records:
            info = zipfile.ZipInfo(record["path"], date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with (ROOT / record["path"]).open("rb") as source_file, bundle.open(info, "w", force_zip64=True) as target:
                shutil.copyfileobj(source_file, target, length=1024 * 1024)
    result = {
        "schema_version": 1,
        "asset_url": ASSET_URL,
        "archive_sha256": digest(ARCHIVE),
        "archive_bytes": ARCHIVE.stat().st_size,
        "source_snapshot_sha256": digest(PROVENANCE),
        "files": records,
    }
    MANIFEST.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"archive": str(ARCHIVE), "manifest": str(MANIFEST), "files": len(records),
            "archive_mib": round(result["archive_bytes"] / 1024**2, 2), "sha256": result["archive_sha256"]}


def fetch() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if digest(PROVENANCE) != manifest["source_snapshot_sha256"]:
        raise ValueError("Release manifest does not match this code snapshot")
    records = manifest["files"]
    expected = {record["path"] for record in records}
    if any(not path.startswith("data/") or Path(path).is_absolute() or ".." in Path(path).parts for path in expected):
        raise ValueError("Unsafe release path")
    for record in records:
        path = ROOT / record["path"]
        if path.is_file() and digest(path) != record["sha256"]:
            raise ValueError(f"Existing data differs: {record['path']}")
    if all((ROOT / record["path"]).is_file() for record in records):
        return {"status": "already_present", "files": len(records)}
    scratch_root = (ROOT / "tmp").resolve()
    scratch_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ncd-release-", dir=scratch_root) as temporary:
        if not Path(temporary).resolve().is_relative_to(scratch_root):
            raise ValueError("Download scratch escaped workspace")
        download = Path(temporary) / "archive.zip"
        request = urllib.request.Request(manifest["asset_url"], headers={"User-Agent": "ncd-gemma-public-data/1"})
        with urllib.request.urlopen(request, timeout=120) as response, download.open("wb") as target:
            shutil.copyfileobj(response, target, length=1024 * 1024)
        if download.stat().st_size != manifest["archive_bytes"] or digest(download) != manifest["archive_sha256"]:
            raise ValueError("Release archive hash/size mismatch")
        with zipfile.ZipFile(download) as bundle:
            if len(bundle.namelist()) != len(expected) or set(bundle.namelist()) != expected:
                raise ValueError("Release file list mismatch")
            for record in records:
                output = Path(temporary) / record["path"]
                output.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(record["path"]) as source, output.open("wb") as target:
                    shutil.copyfileobj(source, target, length=1024 * 1024)
                if output.stat().st_size != record["bytes"] or digest(output) != record["sha256"]:
                    raise ValueError(f"Release file hash mismatch: {record['path']}")
            for record in records:
                destination = ROOT / record["path"]
                if not destination.exists():
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(Path(temporary) / record["path"]), str(destination))
    return {"status": "downloaded", "files": len(records)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["package", "fetch"])
    args = parser.parse_args()
    print(json.dumps(package() if args.action == "package" else fetch()))


if __name__ == "__main__":
    main()
