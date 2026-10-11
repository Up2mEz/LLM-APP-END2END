"""Deterministic PDF cell transcription; never reads evaluation questions."""
from __future__ import annotations

import re


def compact(value):
    return re.sub(r"\s+", "", value or "")


def numeric(value):
    return bool(re.fullmatch(r"[\d.,%*+<>≤≥/()\-–—]+", compact(value)))


def transcribe_table(page, table):
    """Use cell geometry for merged headers, with a left row-label fallback."""
    extracted = table.extract()
    data_start = next((i for i, row in enumerate(extracted)
                       if sum(numeric(v) for v in row) >= max(2, len(row)-2)), None)
    if data_start is None or data_start == 0:
        return None
    headers = []
    data_cells = table.rows[data_start].cells
    for cell in data_cells:
        if cell is None:
            return None
        x = (cell[0] + cell[2]) / 2
        parts = []
        for ri, row in enumerate(table.rows[:data_start]):
            for ci, header in enumerate(row.cells):
                if header and header[0] <= x <= header[2]:
                    label = compact(extracted[ri][ci])
                    if label and label not in parts:
                        parts.append(label)
        headers.append(" / ".join(parts))
    if not all(headers):
        return None
    # A missing outer border can omit the first column. Associate nearby words
    # by their centre, avoiding glyph boxes that overlap adjacent row boundaries.
    words = page.get_text("words")
    def left_text(y0, y1):
        selected = [w for w in words if max(0, table.bbox[0]-150) <= (w[0]+w[2])/2 < table.bbox[0]
                    and y0 <= (w[1]+w[3])/2 < y1]
        return compact(" ".join(w[4] for w in sorted(selected, key=lambda w: (round(w[1]/3), w[0]))))
    left_header = left_text(table.bbox[1], table.rows[data_start].bbox[1])
    records = []
    for i in range(data_start, len(extracted)):
        row = extracted[i]
        if any(v is None for v in row) or sum(numeric(v) for v in row) < max(2, len(row)-2):
            continue
        values = [compact(v) for v in row]
        cells = dict(zip(headers, values))
        if left_header and all(numeric(v) for v in values):
            label = left_text(table.rows[i].bbox[1], table.rows[i].bbox[3])
            if not label:
                continue
            cells = {left_header: label, **cells}
        records.append({"cells": cells, "bbox": list(table.rows[i].bbox)})
    return {"bbox": list(table.bbox), "rows": records} if records else None


def table_lines(table):
    return [f"ตาราง PDF หน้า {table['pdf_page']}: " + "; ".join(f"C{i} {k} = {v}" for i, (k, v) in enumerate(row["cells"].items()))
            for row in table["rows"]]


def render_table_selection(raw, sources):
    """Render selected cells with their actual headers, not generated meanings."""
    from .evidence import line_quote
    if not set(raw) <= {'status', 'table_cells', 'answer', 'citations'} or raw.get('status') != 'answered':
        raise ValueError('Invalid table answer fields')
    selections = raw['table_cells']
    if not isinstance(selections, list) or not 1 <= len(selections) <= 4:
        raise ValueError('Select 1..4 table rows')
    answers, ranges = [], {}
    for selected in selections:
        if not isinstance(selected, dict) or set(selected) != {'source_id', 'line', 'columns'}:
            raise ValueError('Table selection needs source_id, line, columns')
        sid, line, columns = selected['source_id'], selected['line'], selected['columns']
        if sid not in sources:
            raise ValueError('Unknown table source ID')
        line = resolve_table_line(sources[sid], line)
        quote = line_quote(sources[sid], line, line)
        cells = re.split(r'; (?=C\d+ )', quote.split(': ', 1)[1])
        if (not isinstance(columns, list) or not 1 <= len(columns) <= 4
                or any(type(c) is not int or not 1 <= c < len(cells) for c in columns)
                or len(set(columns)) != len(columns)):
            raise ValueError('Select 1..4 distinct value column indices, excluding C0')
        clean = lambda s: re.sub(r'^C\d+ ', '', s)
        answers.append(clean(cells[0]) + ': ' + '; '.join(clean(cells[i]) for i in columns) + f' [{sid}]')
        ranges.setdefault(sid, []).append(line)
    citations = [{'source_id':sid, 'quote':line_quote(sources[sid], min(lines), max(lines))} for sid,lines in ranges.items()]
    return {'status':'answered','answer':'\n'.join(answers),'citations':citations}


def resolve_table_line(source, number):
    """Map an exact flattened numeric row to its uniquely matching cell row."""
    from .evidence import line_quote
    quote = line_quote(source, number, number)
    if re.match(r'^ตาราง PDF หน้า \d+: C0 ', quote):
        return number
    target = re.findall(r'\d+(?:\.\d+)?', quote)
    if len(target) < 4 or len(re.sub(r'[\d\s.*%|:/()\-–—]', '', quote)) > 10:
        raise ValueError('Selected line must be a structured PDF table row')
    matches = []
    for i, candidate in enumerate(source['text'].splitlines(), 1):
        if not re.match(r'^ตาราง PDF หน้า \d+: C0 ', candidate):
            continue
        cells = re.split(r'; (?=C\d+ )', candidate.split(': ',1)[1])
        values = [v for c in cells for v in re.findall(r'\d+(?:\.\d+)?', c.split(' = ',1)[1])]
        if values == target:
            matches.append(i)
    if len(matches) != 1:
        raise ValueError('Numeric row has no unique structured table match')
    return matches[0]


def reviewed_table_answer(review, sources):
    """For an entirely tabular answer, present all cells of the verified rows.

    This prevents a reviewer from approving a missing part while displaying
    only a subset of that row's facts. Semantic row selection still needs review.
    """
    selected = []
    for check in review.checks:
        if not hasattr(check, 'start_line') or check.start_line != check.end_line:
            return None
        source = sources.get(check.source_id, {})
        try:
            line = resolve_table_line(source, check.start_line)
        except (ValueError, KeyError):
            return None
        key = (check.source_id, line)
        if key not in selected:
            selected.append(key)
    if not 1 <= len(selected) <= 4:
        return None
    answers, citations = [], {}
    from .evidence import line_quote
    for sid, line in selected:
        quote = line_quote(sources[sid], line, line)
        facts = re.sub(r'(^|; )C\d+ ', r'\1', quote.split(': ', 1)[1])
        answers.append(facts + f' [{sid}]')
        citations.setdefault(sid, []).append(line)
    return {'status':'answered', 'answer':'\n'.join(answers), 'citations':[
        {'source_id':sid,'quote':line_quote(sources[sid], min(lines),max(lines))} for sid,lines in citations.items()]}
