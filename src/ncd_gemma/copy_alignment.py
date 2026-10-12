"""Recover a near-verbatim copy by returning actual source characters only.

This is not entailment or paraphrase acceptance. Changed numbers, Latin tokens,
comparators and Thai negations are rejected; normal evidence review still runs.
"""
from copy import deepcopy
from difflib import SequenceMatcher
import re

from .evidence import line_quote, span_range


def protected(text):
    tokens = re.findall(r'[A-Za-z][A-Za-z0-9_-]*|\d+(?:\.\d+)?|[<>≤≥=%]', text)
    controls = ('ไม่', 'ห้าม', 'งด', 'น้อยกว่า', 'มากกว่า', 'เกิน', 'ต่ำกว่า', 'สูงกว่า')
    return tokens, tuple(text.count(t) for t in controls)


def anchor_copy(candidate, source):
    needle = re.sub(r'\s+', '', candidate)
    positions = [i for i,c in enumerate(source) if not c.isspace()]
    hay = ''.join(source[i] for i in positions)
    if needle in hay or len(needle) < 60:
        return candidate
    blocks = [b for b in SequenceMatcher(None, needle, hay, autojunk=False).get_matching_blocks() if b.size]
    if not blocks:
        return candidate
    start = max(0, blocks[0].b - blocks[0].a)
    end = min(len(hay), blocks[-1].b + blocks[-1].size + len(needle)-blocks[-1].a-blocks[-1].size)
    actual = hay[start:end]
    matcher = SequenceMatcher(None, needle, actual, autojunk=False)
    edits = sum(max(b-a,d-c) for tag,a,b,c,d in matcher.get_opcodes() if tag != 'equal')
    if edits > max(2,int(len(needle)*.03)) or matcher.ratio()<.97 or protected(needle)!=protected(actual):
        return candidate
    return source[positions[start]:positions[end-1]+1]


def align_claim_copies(raw, sources):
    if not isinstance(raw,dict) or not isinstance(raw.get('claims'),list):
        return raw
    result=deepcopy(raw)
    for claim in result['claims']:
        if not isinstance(claim,dict) or not isinstance(claim.get('text'),str) or claim.get('source_id') not in sources:
            continue
        try:
            source=sources[claim['source_id']]
            a,b=span_range(source,claim.get('span_ids'))
            claim['text']=anchor_copy(claim['text'],line_quote(source,a,b))
        except (ValueError,TypeError):
            continue  # Ordinary schema validation reports the invalid selection.
    return result


def missing_requested_dimension(question, answer):
    """Narrow lexical completeness gates, never a correctness score."""
    if any(t in question for t in ('รอบใด','รอบไหน','รอบที่เท่า')) and 'รอบ' not in answer:
        return 'The question asks which round. A section number is not a round. Copy the round and its condition from evidence.'
    if any(t in question for t in ('สัดส่วน','กี่เปอร์เซ็นต์','ร้อยละเท่า')) and not any(t in answer for t in ('ร้อยละ','เปอร์เซ็นต์','%','/')):
        return 'The question asks a proportion. Give its unit or denominator, and the named subgroup, not bare numbers.'
    if 'ความถี่' in question and not any(t in answer for t in ('ครั้ง','ทุก','เว้นวัน')):
        return 'The question asks frequency as well as amount. A dose per day does not state how many times to take it. Copy the frequency from the same evidence row.'
    if (re.search(r'ต่างกัน|เปรียบเทียบ', question) and 'ไหลเวียน' in question
            and 'คงที่' in question and 'ต่ำ' in question
            and not (('คงที่' in answer or 'stable' in answer.casefold()) and 'ต่ำ' in answer)):
        return 'The question compares stable circulation with low blood pressure. Answer both situations, including the method for the stable group.'
    if 'ข้อมูลอะไร' in question and 'ฉลาก' in question and answer.startswith('อ่านฉลาก') and not any(t in answer for t in ('ปริมาณ','จำนวน','ค่า','วันหมด','ส่วนประกอบ','ชื่อ','ขนาด')):
        return 'Name the specific information field on the label from evidence. Merely saying to read the label does not answer which information to look for.'
    if (re.search(r'ความดัน.{0,20}เท่า(?:ไร|ไหร่)', question)
            and re.search(r'เกิน|มากกว่า|ต่ำกว่า|น้อยกว่า', question)
            and not re.search(r'เปรียบเทียบ|แตกต่าง|แต่ละ|ทั้งสอง|ระหว่าง', question)
            and len(set(re.findall(r'\b\d{2,3}\s*/\s*\d{2,3}\b', answer))) > 1):
        return 'The question specifies one subgroup and asks for one blood-pressure target. Select only the target conditioned on that subgroup; omit the general target.'
    if ('ไตเรื้อรัง' in question and re.search(r'เมื่อมี|ร่วมด้วย', question)
            and 'ถ้าไม่อิ่ม' in answer and 'ไตเรื้อรัง' not in answer):
        return 'Do not substitute an unrelated if-not-full condition for the requested chronic-kidney-disease condition. Include the disease context and the corresponding food change from evidence.'
    if 'ยา' not in question and any(t in answer for t in ('ให้เริ่มด้วยยา','แนะนำให้ยา','เริ่ม ด้วยยา')):
        return 'Do not add drug-treatment instructions when the question asks only for dietary or measurement targets. Select only the requested target and its qualifying condition.'
    return None
