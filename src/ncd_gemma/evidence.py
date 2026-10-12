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
    return (numeric_rows >= 2 or bool(re.search(r"\|[^\n]+\|\n\s*\|?\s*:?-{3}", text))
            # Some frozen corpus tables are HTML fragments split across parent
            # chunks. The header hit must bring in its adjacent data rows.
            or bool(re.search(r'<(?:table|tr|t[dh])(?:\s|>)', text, re.I)))


def table_answer_route(hit: dict) -> bool:
    """Text-extracted headers also need row/header reasoning, not prose copying."""
    text = hit['text']
    return bool(hit.get('table_provenance') or table_like(text)
                or re.search(r'จำนวน\s*(?:\([^)]*\))?\s+ร้อยละ', text)
                or ('ชนิดของยา' in text and 'ขนาดยา' in text))


def explicit_row_lookup(question: str) -> bool:
    return 'ความถี่' in question or ('จำนวน' in question and 'สัดส่วน' in question)


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
            # A retrieved parent can end just before a recommendation. Include
            # bounded neighbouring text from the same admitted document/edition.
            neighbors = self.neighbors.get(hit['chunk_id'], [])
            selected = [x for x in neighbors if x['pdf_page_end'] >= hit['pdf_page_start'] - 1
                        and x['pdf_page_start'] <= hit['pdf_page_end'] + 1]
            if len(selected) <= 1:
                return hit
            parts = []
            for x in selected:
                if x['chunk_id'] == hit['chunk_id']:
                    parts.append(x['text'])
                elif (x['pdf_page_start'], x.get('char_start', 0)) < (hit['pdf_page_start'], hit.get('char_start', 0)):
                    # A comparison can begin near the start of the preceding
                    # parent (e.g. conventional dialysis vs SLED). Keep the
                    # preceding recommendation, within the same edition.
                    parts.append(x['text'][-1600:])
                else:
                    parts.append(x['text'][:1200])
            return {**hit, 'text': '\n'.join(parts), 'context_enriched': True,
                    'pdf_page_start': min(x['pdf_page_start'] for x in selected),
                    'pdf_page_end': max(x['pdf_page_end'] for x in selected),
                    'context_chunks': [{k:x[k] for k in ('chunk_id','pdf_page_start','pdf_page_end')} for x in selected],
                    'table_provenance': []}
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


def evidence_spans(source: dict) -> list[dict]:
    """Stable, bounded passage choices; numbers are generated locally, not guessed."""
    spans, buffer, start = [], [], 1
    lines = source['text'].splitlines()
    for i, line in enumerate(lines, 1):
        if buffer and sum(len(s) + 1 for s in buffer) + len(line) > 1700:
            spans.append({'span_id': f'P{len(spans)+1}', 'start_line': start,
                          'end_line': i-1, 'text': '\n'.join(buffer)})
            buffer, start = [], i
        buffer.append(line)
    if buffer:
        spans.append({'span_id': f'P{len(spans)+1}', 'start_line': start,
                      'end_line': len(lines), 'text': '\n'.join(buffer)})
    return spans


def span_range(source: dict, span_ids: list[str]) -> tuple[int, int]:
    choices = {p['span_id']:p for p in evidence_spans(source)}
    if not isinstance(span_ids, list) or not 1 <= len(span_ids) <= 3 or any(type(p) is not str or p not in choices for p in span_ids):
        raise ValueError('Select 1..3 existing span_ids from this source')
    start = min(choices[p]['start_line'] for p in span_ids)
    end = max(choices[p]['end_line'] for p in span_ids)
    line_quote(source, start, end)  # Reject oversized/non-contiguous unions, never clamp.
    return start, end


def model_evidence(source: dict) -> dict:
    # Hashes and bounding boxes remain in the trace but do not consume model context.
    return {k:source[k] for k in ('source_id','document_id','edition_id','pdf_page_start','pdf_page_end') if k in source} | {
        'passages': [{**p, 'text': '\n'.join(f'{i}: {s}' for i,s in enumerate(p['text'].splitlines(),p['start_line']))}
                     for p in evidence_spans(source)]}
