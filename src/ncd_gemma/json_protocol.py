"""Narrow, non-semantic repair of one observed Gemma JSON formatting defect."""
import json
import re


def load_json(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # The proxy can emit ,""end_line":4 instead of ,"end_line":4.
    # Fix only duplicate opening quotes on a property outside string values.
    # Never change values, close an unfinished response, or evaluate code.
    out, inside, escaped, changes, previous = [], False, False, 0, ''
    i = 0
    while i < len(text):
        c = text[i]
        if not inside and previous in ('{', ',') and c == '"':
            match = re.match(r'""([A-Za-z_][A-Za-z0-9_]*)"\s*:', text[i:])
            if match:
                changes += 1
                i += 1
        c = text[i]
        out.append(c)
        if inside:
            if escaped:
                escaped = False
            elif c == '\\':
                escaped = True
            elif c == '"':
                inside = False
        elif c == '"':
            inside = True
        if not c.isspace():
            previous = c
        i += 1
    if not 1 <= changes <= 4:
        return json.loads(text)  # Preserve a parse error for all other defects.
    return json.loads(''.join(out))
