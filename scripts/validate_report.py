"""Validate and render the report; record visual review only when explicitly attested."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "output/pdf/NCD_GEMMA_PROJECT_REPORT_TH.pdf"
RENDERS = ROOT / "tmp/pdfs"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--visual-reviewed", action="store_true",
                        help="Use only after inspecting every rendered page of this exact PDF")
    args = parser.parse_args()
    document = pymupdf.open(PDF)
    if not 4 <= len(document) <= 8:
        raise ValueError(f"Expected 4 to 8 pages, got {len(document)}")
    text = "\n".join(page.get_text() for page in document)
    # Shaped Thai extraction may contain a decomposed sara am, so do not compare
    # entire Thai paragraphs byte-for-byte. Latin figures remain unambiguous.
    tests = json.loads((ROOT / "reports/evaluation_tests_2026-10-20.json").read_text(encoding="utf-8"))
    latest = json.loads((ROOT / "reports/evaluations/v32/dev_metrics.json").read_text(encoding="utf-8"))
    audit = json.loads((ROOT / "reports/evaluations/v32/dev_semantic_audit.json").read_text(encoding="utf-8"))
    extra = json.loads((ROOT / "reports/evaluations/v32/extra_semantic_audit.json").read_text(encoding="utf-8"))
    expected = ("6707060", "0.8077", "0.8846", "0.9135", "0.6181", "0.7374", "0.7706",
                f"{latest['mean_character_f1_answerable']:.4f}",
                f"{latest['citation_primary_evidence_hit_rate_answerable']:.4f}",
                f"{len(audit['core_matches'])}/25", f"{extra['strict_correct']}/30",
                "19/30", "27/30", "30/30", str(tests["tests_passed"]), "v31", "v32", "llm.py", "config.py")
    missing = [value for value in expected if value not in text]
    if missing:
        raise ValueError(f"Report is missing measured claims: {missing}")
    prohibited = [c for c in text if c == "\ufffd" or "\u4e00" <= c <= "\u9fff" or c in "→–—•"]
    if prohibited:
        raise ValueError(f"Unexpected glyphs: {sorted(set(prohibited))}")
    overflow = []
    for i,page in enumerate(document):
        for block in page.get_text("blocks"):
            rect = pymupdf.Rect(block[:4])
            if not page.rect.contains(rect):
                overflow.append(i+1)
    if overflow:
        raise ValueError(f"Text outside page bounds: {overflow}")
    RENDERS.mkdir(parents=True,exist_ok=True)
    rendered = []
    for i,page in enumerate(document):
        path = RENDERS / f"report-final-{i+1}.png"
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False)
        rendered_bytes = pixmap.tobytes("png")
        # Do not claim a visual check for an older render.
        if args.visual_reviewed and (not path.exists() or path.read_bytes() != rendered_bytes):
            raise ValueError(f"Page {i+1} changed since rendering; inspect again before attesting")
        path.write_bytes(rendered_bytes)
        rendered.append({"page":i+1,"path":path.relative_to(ROOT).as_posix(),"sha256":sha(path)})
    report = {
        "recorded_at_utc":datetime.now(timezone.utc).isoformat(),
        "path":PDF.relative_to(ROOT).as_posix(),"sha256":sha(PDF),"pages":len(document),
        "rendered_pages":rendered,
        "all_pages_visually_reviewed":args.visual_reviewed,
        "checks":["4 to 8 pages","measured values present","no replacement glyph, CJK text or decorative dash/arrow/bullet","text within page bounds"],
        "scope":"Document content and layout checks. No new LLM evaluation or independent clinical review.",
    }
    output = ROOT / "reports/pdf_validation_2026-10-20.json"
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"pages":report["pages"],"sha256":report["sha256"],"visual_reviewed":args.visual_reviewed}))


if __name__ == "__main__":
    main()
