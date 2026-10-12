"""Render claim/citation structure without requiring the model to type markers."""
from __future__ import annotations
import re
from copy import deepcopy
from .evidence import line_quote, span_range


def bind_existing_markers(raw: dict, sources: dict) -> dict:
    """Format-only recovery: bind model-named IDs to whole short passages.

    Never select a new source or infer a fact. The normal schema, quote and
    semantic checks still apply after this normalization.
    """
    if not isinstance(raw,dict) or raw.get('status')!='answered' or not isinstance(raw.get('answer'),str):
        return raw
    ids=list(dict.fromkeys(re.findall(r'S\d+', ''.join(re.findall(r'\[(S\d+(?:\s*[,;]\s*S\d+)*)\]',raw['answer'])))))
    if set(raw)=={'status','answer'} and ids and all(s in sources and 8<=len(sources[s]['text'].strip())<=1800 for s in ids):
        return {**raw,'citations':[{'source_id':s,'quote':sources[s]['text'].strip()} for s in ids]}
    if not ids and isinstance(raw.get('citations'),list) and raw['citations'] and all(isinstance(c,dict) and c.get('source_id') in sources for c in raw['citations']):
        return {**raw,'answer':raw['answer']+' '+ ' '.join('['+c['source_id']+']' for c in raw['citations'])}
    return raw


def render_claims(raw: dict, sources: dict, require_verbatim: bool = True) -> dict:
    if set(raw) != {'status','claims'} or raw['status'] != 'answered':
        raise ValueError('Use status answered and claims only')
    claims = raw['claims']
    if not isinstance(claims,list) or not 1 <= len(claims) <= 5:
        raise ValueError('Select 1..5 claims covering the question')
    sentences, spans = [], {}
    for index, claim in enumerate(claims, 1):
        if not isinstance(claim,dict) or set(claim) != {'text','source_id','span_ids'}:
            raise ValueError('Each claim needs text, source_id and span_ids')
        sid, text = claim['source_id'], claim['text']
        if not isinstance(sid,str) or sid not in sources:
            raise ValueError('Unknown claim source ID')
        if not isinstance(text,str) or not 1 <= len(text.strip()) <= 1200 or re.search(r'\[S\d',text):
            raise ValueError('Claim text must be 1..1200 characters without citation markers')
        a,b = span_range(sources[sid],claim['span_ids'])
        excerpt=line_quote(sources[sid],a,b)
        compact=lambda value: re.sub(r'\s+','',value)
        needle=compact(text)
        if require_verbatim and needle not in compact(excerpt):
            raise ValueError('Claim text must be an exact excerpt from its selected passage, allowing whitespace only. Copy the requested fact; do not add translations or rewrite its meaning')
        old = spans.get(sid,(a,b))
        spans[sid] = min(a,old[0]),max(b,old[1])
        sentences.append(f'{text.strip()} [{sid}]')
    citations = [{'source_id':sid,'quote':line_quote(sources[sid],a,b)} for sid,(a,b) in spans.items()]
    return {'status':'answered','answer':' '.join(sentences),'citations':citations}


def prune_invalid_claims(raw: dict, sources: dict) -> dict:
    """Keep model-selected claims that are exact copies of their own spans.

    Gemma sometimes emits several redundant candidate claims, one paraphrased
    and another copied correctly. A bad duplicate must not invalidate the
    source-identical one. Missing dimensions still fail the separate review.
    Never select a source or a fragment on behalf of the model.
    """
    if not isinstance(raw, dict) or set(raw) != {'status', 'claims'} or raw['status'] != 'answered':
        return raw
    claims = raw['claims']
    if not isinstance(claims, list) or not 1 < len(claims) <= 5:
        return raw
    valid, seen = [], set()
    for claim in claims:
        try:
            render_claims({'status': 'answered', 'claims': [claim]}, sources)
        except (ValueError, KeyError, TypeError):
            continue
        key = (claim['source_id'], re.sub(r'\s+', '', claim['text']))
        if key not in seen:
            valid.append(claim)
            seen.add(key)
    return {**raw, 'claims': valid} if valid and len(valid) < len(claims) else raw


def repair_verbatim_legacy_citation(raw: dict, sources: dict) -> dict:
    """Fix a guessed line number only when the entire answer is in that source.

    Some Gemma responses use the older answer/citations schema despite a
    span-ID prompt. We never infer a source or an answer: the model must name
    one source, and its answer (ignoring whitespace) must occur exactly once
    in the supplied source. The server then copies the actual characters and
    line range. Otherwise ordinary validation rejects the response.
    """
    if not isinstance(raw, dict) or raw.get('status') != 'answered' or 'claims' in raw or 'table_cells' in raw:
        return raw
    citations = raw.get('citations')
    if not isinstance(citations, list) or len(citations) != 1 or not isinstance(citations[0], dict):
        return raw
    citation = citations[0]
    sid = citation.get('source_id')
    if sid not in sources or set(citation) != {'source_id', 'start_line', 'end_line'}:
        return raw
    try:
        line_quote(sources[sid], citation['start_line'], citation['end_line'])
        return raw  # A valid line selection belongs to the normal path.
    except ValueError:
        pass
    answer = raw.get('answer')
    if not isinstance(answer, str):
        return raw
    match = re.fullmatch(r'(.+?)\s*\[' + re.escape(sid) + r'\]\s*', answer, re.S)
    if match is None or re.search(r'\[S\d+', match.group(1)):
        return raw
    needle = re.sub(r'\s+', '', match.group(1))
    if len(needle) < 15:
        return raw
    source = sources[sid]['text']
    positions = [i for i, char in enumerate(source) if not char.isspace()]
    hay = ''.join(source[i] for i in positions)
    if hay.count(needle) != 1:
        return raw
    at = hay.index(needle)
    start, end = positions[at], positions[at + len(needle) - 1] + 1
    excerpt = source[start:end].strip()
    first = source.count('\n', 0, start) + 1
    last = source.count('\n', 0, end - 1) + 1
    try:
        line_quote(sources[sid], first, last)
    except ValueError:
        return raw
    fixed = deepcopy(raw)
    fixed['answer'] = excerpt + f' [{sid}]'
    fixed['citations'] = [{'source_id': sid, 'start_line': first, 'end_line': last}]
    return fixed


def reviewed_claims(verdict, sources: dict) -> dict | None:
    """Release only exact candidate fragments explicitly supported by the review.

    This cannot prove entailment; it prevents unreviewed extra advice surviving a
    review that covered only the requested core. Tables use their own renderer.
    """
    if not verdict.supported or not all(getattr(c,'answer_quote',None) and hasattr(c,'start_line') for c in verdict.checks):
        return None
    sentences, ranges = [], {}
    for c in verdict.checks:
        fragment = re.sub(r'\[S\d+(?:\s*[,;]\s*S\d+)*\]', '', c.answer_quote).strip()
        sentence = f'{fragment} [{c.source_id}]'
        if sentence not in sentences:
            sentences.append(sentence)
        a,b = ranges.get(c.source_id,(c.start_line,c.end_line))
        ranges[c.source_id] = min(a,c.start_line),max(b,c.end_line)
    citations = [{'source_id':sid,'quote':line_quote(sources[sid],a,b)} for sid,(a,b) in ranges.items()]
    return {'status':'answered','answer':' '.join(sentences),'citations':citations}
