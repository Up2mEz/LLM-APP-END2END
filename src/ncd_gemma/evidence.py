"""Present frozen evidence with adjacent table context and deterministic line IDs.

No question, gold label, or generated answer is used to enrich a retrieved hit.
"""
from __future__ import annotations

import re
from collections import defaultdict


def table_like(text: str) -> bool:
    numeric_rows = sum(len(re.findall(r"\d+(?:\.\d+)?", line)) >= 4
                       and len(re.sub(r"[\d\s.*%|:/()\-–—]", "", line)) < 25
                       for line in text.splitlines())
    return numeric_rows >= 2 or bool(re.search(r"\|[^\n]+\|\n\s*\|?\s*:?-{3}", text))


class TableContext:
    def __init__(self, parents, tables=()):
        groups = defaultdict(list)
        for item in parents:
            groups[item["document_id"], item["edition_id"]].append(item)
        self.neighbors = {}
        self.tables = defaultdict(list)
        for table in tables:
            self.tables[table['document_id'], table['edition_id']].append(table)
        for group in groups.values():
            group.sort(key=lambda x: (x["pdf_page_start"], x.get("char_start", 0)))
            for i, item in enumerate(group):
                self.neighbors[item["chunk_id"]] = group[max(0, i-1):i+2]

    def enrich(self, hit):
        if not table_like(hit["text"]):
            return hit
        selected = []
        for item in self.neighbors.get(hit["chunk_id"], []):
            adjacent = (item["pdf_page_end"] >= hit["pdf_page_start"] - 1
                        and item["pdf_page_start"] <= hit["pdf_page_end"] + 1)
            # Expand only indexable chunks already present in the frozen index.
            if adjacent:
                selected.append(item)
        if not selected:
            return hit
        from .pdf_tables import table_lines
        page_start = min(x['pdf_page_start'] for x in selected)
        page_end = max(x['pdf_page_end'] for x in selected)
        tables = [t for t in self.tables[hit['document_id'], hit['edition_id']]
                  if page_start <= t['pdf_page'] <= page_end]
        structured = [line for t in tables for line in table_lines(t)]
        text = ("ตารางจัดรูปจากเซลล์ PDF โดยคงหัวคอลัมน์และค่าต้นฉบับ\n" + "\n".join(structured) + "\nข้อความต้นฉบับ:\n" if structured else "")
        text += "\n".join(item["text"] for item in selected)
        return {**hit, "text": text,
                "pdf_page_start": page_start,
                "pdf_page_end": page_end,
                "table_provenance": [{k:t[k] for k in ('pdf_page', 'bbox', 'pdf_sha256')} for t in tables],
                "context_chunks": [{k: x[k] for k in ("chunk_id", "pdf_page_start", "pdf_page_end")} for x in selected],
                "context_enriched": True}


def numbered_text(text: str) -> str:
    return "\n".join(f"{i}: {line}" for i, line in enumerate(text.splitlines(), 1))


def line_quote(source: dict, start: int, end: int) -> str:
    lines = source["text"].splitlines()
    if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(lines):
        raise ValueError("Citation line range is outside supplied evidence")
    quote = "\n".join(lines[start - 1:end]).strip()
    if not 8 <= len(quote) <= 1800:
        raise ValueError("Select an evidence line range with 8..1800 characters")
    return quote


def model_evidence(source: dict) -> dict:
    return {k: v for k, v in source.items() if k != "text"} | {"numbered_text": numbered_text(source["text"])}
