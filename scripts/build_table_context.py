"""Read source PDFs without modifying them; write local derived evidence only."""
import argparse
import json
from collections import defaultdict
from pathlib import Path

import pymupdf

from ncd_gemma.config import ROOT
from ncd_gemma.evidence import table_like
from ncd_gemma.pdf_tables import compact, transcribe_table
from ncd_gemma.retrieval import file_hash

parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path, required=True)
args = parser.parse_args()
parents = [json.loads(s) for s in (ROOT / "data/index/chunks-v12-t512/chunks.jsonl").read_text(encoding="utf-8").splitlines()]
admitted, candidates = defaultdict(list), set()
for p in parents:
    for page in range(p["pdf_page_start"], p["pdf_page_end"] + 1):
        key = (p["document_id"], p["edition_id"], page)
        admitted[key].append(p["text"])
        if table_like(p["text"]):
            candidates.add(key)
by_doc = defaultdict(list)
for key in candidates:
    by_doc[key[:2]].append(key[2])
tables, files, skipped = [], [], 0
for (document_id, edition_id), pages in sorted(by_doc.items()):
    path = args.source / "data/raw" / document_id / "source.pdf"
    if not path.is_file():
        skipped += len(pages)
        continue
    source_hash = file_hash(path)
    files.append({"path": str(path), "sha256": source_hash})
    with pymupdf.open(path) as doc:
        for number in sorted(pages):
            page = doc[number-1]
            allowed = compact("".join(admitted[document_id, edition_id, number]))
            for table in page.find_tables().tables:
                record = transcribe_table(page, table)
                if not record:
                    continue
                # Reject transcriptions with cells outside indexable text.
                rows = [r for r in record["rows"] if all(compact(v) in allowed for v in r["cells"].values())]
                if not rows:
                    continue
                tables.append({**record, "rows": rows, "document_id": document_id,
                               "edition_id": edition_id, "pdf_page": number, "pdf_sha256": source_hash})
    print(json.dumps({"document": document_id, "pages": len(pages)}, ensure_ascii=False), flush=True)
dest = ROOT / "data/table_context/tables.jsonl"
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in tables), encoding="utf-8")
manifest = {"method": "PDF geometry and merged header cells; no gold or question input",
            "candidate_pages": len(candidates), "tables": len(tables), "skipped_missing_pdf_pages": skipped,
            "sha256": file_hash(dest), "source_pdfs": files}
(ROOT / "private/table_context_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps({k:v for k,v in manifest.items() if k != "source_pdfs"}))
