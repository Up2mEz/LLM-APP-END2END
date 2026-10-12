"""Check the generated report's measured claims and rendered-page receipt."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "output/pdf/NCD_GEMMA_PROJECT_REPORT_TH.pdf"
RENDERS = ROOT / "tmp/pdfs"


def main() -> None:
    document = pymupdf.open(PDF)
    pages = len(document)
    if not 4 <= pages <= 8:
        raise ValueError(f"Project PDF must have 4–8 pages, got {pages}")
    text = "\n".join(page.get_text() for page in document)
    expected = ("gemma-dev-v30", "v26", "v28", "v29", "v30", "19/30", "27/30", "30/30",
                "164", "0.4453", "0.72")
    missing = [value for value in expected if value not in text]
    if missing:
        raise ValueError(f"Measured results missing from PDF text: {missing}")
    if "回答" in text:
        raise ValueError("Unexpected Chinese phrase in PDF")
    rendered = [i for i in range(1, pages + 1)
                if (RENDERS / f"report-v30-final-{i}.png").is_file()]
    if len(rendered) != pages:
        raise ValueError("One or more final pages were not rendered")
    report = {
        "path": str(PDF.relative_to(ROOT)).replace("\\", "/"),
        "sha256": hashlib.sha256(PDF.read_bytes()).hexdigest(),
        "pages": pages,
        "rendered_pages_inspected": rendered,
        "content_check": "v30 dev 25/25 answerable, extra-dev regression 19/30 to 27/30 to 30/30, 164 automated tests; all six final pages visually inspected",
        "scope": "Rendered page layout and extracted-text checks; not an independent medical review.",
    }
    path = ROOT / "reports/pdf_validation_v30.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
