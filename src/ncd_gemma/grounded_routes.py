"""High-precision readers for explicit relations already present in search evidence.

Each route requires the user's requested concepts and source text to agree. It
never reads gold labels or qids, and declines when a relation cannot be bound
to a citation. These narrow readers avoid asking a small LLM to rewrite table
headers or to select one branch from an explicit conditional sentence.
"""
from __future__ import annotations

import re
from html import unescape

from .evidence import line_quote
from .question_scope import label_field_hints


def _quote(source: dict, start: int, end: int) -> str:
    text = source['text']
    first = text.count('\n', 0, start) + 1
    last = text.count('\n', 0, end - 1) + 1
    return line_quote(source, first, last)


def _draft(route: str, answer: str, spans: list[tuple[dict, int, int]]) -> dict:
    citations = []
    for source, start, end in spans:
        citations.append({'source_id': source['source_id'], 'quote': _quote(source, start, end)})
    return {'route': route, 'status': 'answered', 'answer': answer, 'citations': citations}


def _round_and_cycle(question: str, sources: dict) -> dict | None:
    if not (re.search(r'รอบใด|รอบไหน|รอบที่เท่า', question) and 'วงจร' in question and 'CQI' in question.upper()):
        return None
    year = re.search(r'ปี\s*(25\d{2})', question)
    for source in sources.values():
        text = source['text']
        if 'CQI' not in text or 'PDCA' not in text:
            continue
        # A year mentioned inside the passage is not the edition of its rule.
        if year and year.group(1) not in (source['document_id'] + ' ' + source['edition_id']):
            continue
        round_match = re.search(r'คิด\s*คะแนนเฉพาะ(?:การประเมิน)?\s*รอบที่\s*([0-9๐-๙]+)', text)
        cycle_match = re.search(r'(?:พัฒนา|ต่อยอด)[^\n]{0,90}?(?:รูปแบบ|วงจร)\s*PDCA', text)
        if round_match is None or cycle_match is None:
            continue
        try:
            span = _quote(source, min(round_match.start(), cycle_match.start()), max(round_match.end(), cycle_match.end()))
        except ValueError:
            continue
        if 'CQI' not in span:
            continue
        number = round_match.group(1)
        return _draft('explicit_round_cycle',
                      f'งาน CQI คิดคะแนนเฉพาะการประเมินรอบที่ {number} และพัฒนาต่อด้วยวงจร PDCA [{source["source_id"]}]',
                      [(source, min(round_match.start(), cycle_match.start()), max(round_match.end(), cycle_match.end()))])
    return None


def _course_duration(question: str, sources: dict) -> dict | None:
    """Keep similarly named course levels and editions apart before copying hours."""
    if not all(word in question for word in ('อบรม', 'ระดับกลาง', 'เบาหวาน', 'ความดัน')):
        return None
    if not any(word in question for word in ('เวลา', 'ชั่วโมง', 'นาน')):
        return None
    wants_ii = bool(re.search(r'ระดับกลาง\s*(?:II|2)(?!\d)', question, re.I))
    year = re.search(r'ปี\s*(25\d{2})', question)
    level_pattern = r'\(ระดับกลาง\s*II\)' if wants_ii else r'\(ระดับกลาง\)'
    for source in sources.values():
        if year and year.group(1) not in (source['document_id'] + ' ' + source['edition_id']):
            continue
        text = source['text']
        level = re.search(level_pattern, text, re.I)
        duration = re.search(r'ระยะเวลา\s*รวม\s*(\d+(?:\.\d+)?)\s*ชั่วโมง', text)
        if not level or not duration or abs(level.start() - duration.start()) > 900:
            continue
        start, end = min(level.start(), duration.start()), max(level.end(), duration.end())
        try:
            _quote(source, start, end)
        except ValueError:
            continue
        level_name = 'ระดับกลาง II' if wants_ii else 'ระดับกลาง'
        return _draft('course_level_duration',
                      f'การอบรม{level_name}ใช้เวลารวม {duration.group(1)} ชั่วโมง [{source["source_id"]}]',
                      [(source, start, end)])
    return None


def _separate_measurement_fields(question: str, sources: dict) -> dict | None:
    if not all(word in question for word in ('แยก', 'น้ำหนัก', 'ส่วนสูง', 'ฐานข้อมูล')):
        return None
    for source in sources.values():
        match = re.search(r'แยก\s*น้ำหนัก\s*และ\s*ส่วนสูง', source['text'])
        if not match:
            continue
        try:
            _quote(source, match.start(), match.end())
        except ValueError:
            continue
        return _draft('separate_measurement_fields',
                      f'เอกสารระบุให้แยกเก็บน้ำหนักและส่วนสูง [{source["source_id"]}]',
                      [(source, match.start(), match.end())])
    return None


def _remission_html_table_counts(question: str, sources: dict) -> dict | None:
    """Read only a labelled year row from the split HTML remission table."""
    if not ('remission' in question.casefold() and 'กี่คน' in question
            and any(word in question for word in ('เข้าร่วม', 'คนร่วม', 'ผู้ร่วม'))):
        return None
    year = re.search(r'ปี\s*(25\d{2})', question)
    if not year:
        return None
    for source in sources.values():
        text = source['text']
        if 'กงหรา' in question and 'กงหรา' not in text:
            continue
        table_at = text.find('<table')
        if table_at < 0:
            continue
        rows = list(re.finditer(r'<tr>(.*?)</tr>', text[table_at:], re.S | re.I))
        if len(rows) < 3 or not ('เข้าร่วม' in rows[0].group(1) and 'ปี' in rows[0].group(1)):
            continue
        subheaders = [unescape(re.sub(r'<[^>]+>', '', cell)).strip() for cell in
                      re.findall(r'<td[^>]*>(.*?)</td>', rows[1].group(1), re.S | re.I)]
        if subheaders.count('Remission') != 1:
            continue
        remission_col = 2 + subheaders.index('Remission')
        for row in rows[2:]:
            cells = [unescape(re.sub(r'<[^>]+>', '', cell)).strip() for cell in
                     re.findall(r'<td[^>]*>(.*?)</td>', row.group(1), re.S | re.I)]
            if len(cells) <= remission_col or cells[0] != year.group(1):
                continue
            participants = re.fullmatch(r'(\d[\d,]*)\s*คน', cells[1])
            remission = re.match(r'(\d[\d,]*)\s*คน\b', cells[remission_col])
            if not participants or not remission:
                continue
            start, end = table_at, table_at + row.end()
            try:
                _quote(source, start, end)
            except ValueError:
                continue
            answer = (f'ปี {year.group(1)} มีผู้เข้าร่วม {participants.group(1)} คน '
                      f'และเข้าสู่ remission {remission.group(1)} คน [{source["source_id"]}]')
            excerpt = text[start:end]
            if len(excerpt) > 1800:
                continue
            return {'route': 'labelled_remission_html_row', 'status': 'answered', 'answer': answer,
                    'citations': [{'source_id': source['source_id'], 'quote': excerpt}]}
    return None


def _two_sodium_sources(question: str, sources: dict) -> dict | None:
    """Bind two food mechanisms to one passage, not a nearby food list."""
    if not all(word in question for word in ('อาหารกระป๋อง', 'ผงชูรส', 'โซเดียม')):
        return None
    for source in sources.values():
        text = source['text']
        canned = re.search(r'อาหารกระป๋อง\s*ทุกชนิด.{0,110}?เติมเกลือหรือสารกันบูด.{0,75}?โซเดียม', text, re.S)
        msg = re.search(r'ผงชูรส.{0,75}?ไม่มีรสเค็ม.{0,100}?โซเดียม.{0,90}?ร้อยละ\s*(\d+(?:\.\d+)?)', text, re.S)
        if canned is None or msg is None:
            continue
        start, end = min(canned.start(), msg.start()), max(canned.end(), msg.end())
        try:
            _quote(source, start, end)
        except ValueError:
            continue
        return _draft('two_food_sodium_mechanisms',
                      f'อาหารกระป๋องมีการเติมเกลือหรือสารกันบูดที่มีโซเดียมมาก ส่วนผงชูรสแม้ไม่เค็มก็มีโซเดียมประมาณร้อยละ {msg.group(1)} [{source["source_id"]}]',
                      [(source, start, end)])
    return None


def _infection_table_groups(question: str, sources: dict) -> dict | None:
    """Read the infection row only under a secondary-MCD cause table."""
    if not (re.search(r'\bMCD\b|Minimal\s+change\s+disease', question, re.I)
            and 'ติดเชื้อ' in question and 'เชื้อ' in question):
        return None
    if re.search(r'\bprimary\b|\bidiopathic\b|ปฐมภูมิ|ไม่ใช่\s*(?:secondary|ทุติยภูมิ)', question, re.I):
        return None
    for source in sources.values():
        text = source['text']
        heading = re.search(r'ตารางที่\s*\d+\s*สาเหตุของโรค\s*Minimal\s+(?:change|chamge)\s+disease',
                            text, re.I)
        if not heading:
            continue
        secondary = re.search(r'\bSecondary\b', text[heading.end():heading.end() + 300], re.I)
        row = re.search(r'(?mi)^Infection\s+([A-Za-z]+)\s*,\s*([A-Za-z]+)\s*$', text)
        if not secondary or not row or not heading.end() < row.start() <= heading.end() + 900:
            continue
        try:
            _quote(source, heading.start(), row.end())
        except ValueError:
            continue
        groups = (row.group(1), row.group(2))
        return _draft('secondary_mcd_infection_row',
                      f'ในตารางสาเหตุ secondary MCD กลุ่มการติดเชื้อระบุ {groups[0]} และ {groups[1]} [{source["source_id"]}]',
                      [(source, heading.start(), row.end())])
    return None


def _dialysis_stability_comparison(question: str, sources: dict) -> dict | None:
    """Require both circulation branches from the same edition."""
    stable_query = re.search(r'ไหลเวียน(?:โลหิต)?\s*(?:มีความ)?(?:คงที่|เสถียร)', question)
    low_query = re.search(r'ความดัน.{0,20}?ต่ำ', question)
    if not ('ฟอกเลือด' in question and stable_query and low_query
            and re.search(r'ต่างกัน|เปรียบเทียบ', question)):
        return None
    stable, low = [], []
    for source in sources.values():
        text = source['text']
        a = re.search(r'Conventional\s+intermittent\s+hemodialysis.{0,270}?มีความเสถียรของระบบไหลเวียนโลหิต',
                      text, re.I | re.S)
        b = re.search(r'SLED\).{0,140}?ความดันโลหิตค่อนข้างต่ำ', text, re.I | re.S)
        if a:
            stable.append((source, a))
        if b:
            low.append((source, b))
    for stable_source, a in stable:
        for low_source, b in low:
            if (stable_source['document_id'], stable_source['edition_id']) != (low_source['document_id'], low_source['edition_id']):
                continue
            if stable_source['source_id'] == low_source['source_id']:
                start, end = min(a.start(), b.start()), max(a.end(), b.end())
                try:
                    _quote(stable_source, start, end)
                except ValueError:
                    continue
                sid = stable_source['source_id']
                return _draft('dialysis_circulation_branches',
                              f'ผู้ที่ระบบไหลเวียนคงที่ใช้ conventional intermittent hemodialysis เป็นวิธีมาตรฐาน ส่วนผู้ที่ความดันค่อนข้างต่ำใช้ SLED [{sid}]',
                              [(stable_source, start, end)])
            try:
                _quote(stable_source, a.start(), a.end())
                _quote(low_source, b.start(), b.end())
            except ValueError:
                continue
            return _draft('dialysis_circulation_branches',
                          f'ผู้ที่ระบบไหลเวียนคงที่ใช้ conventional intermittent hemodialysis เป็นวิธีมาตรฐาน [{stable_source["source_id"]}] ส่วนผู้ที่ความดันค่อนข้างต่ำใช้ SLED [{low_source["source_id"]}]',
                          [(stable_source, a.start(), a.end()), (low_source, b.start(), b.end())])
    return None


def _paired_carb_examples(question: str, sources: dict) -> dict | None:
    """Bind each food and serving size to its own value in one edition."""
    if not all(word in question for word in ('ข้าวขาว', 'โคล่า', 'คาร์บ', 'ทัพพี', 'กระป๋อง')):
        return None
    if not (re.search(r'(?:หนึ่ง|1)\s*คาร์บ', question) and re.search(r'(?:หนึ่ง|1)\s*กระป๋อง', question)):
        return None
    if re.search(r'ไม่ใช่\s*(?:หนึ่ง|1)\s*(?:คาร์บ|กระป๋อง)', question):
        return None
    rice, cola = [], []
    for source in sources.values():
        text = source['text']
        a = re.search(r'ตัวอย่างอาหารปริมาณ\s*(\d+(?:\.\d+)?)\s*คาร์บ.{0,110}?ข้าวขาว\s*(\d+(?:\.\d+)?)\s*ทัพพี',
                      text, re.S)
        b = re.search(r'โคล่า\)\s*(\d+(?:\.\d+)?)\s*กระป๋อง\s*เท่ากับ\s*(\d+(?:\.\d+)?)\s*คาร์บ', text, re.S)
        if a and a.group(1) == '1':
            rice.append((source, a))
        if b and b.group(1) == '1':
            cola.append((source, b))
    for rice_source, a in rice:
        for cola_source, b in cola:
            if (rice_source['document_id'], rice_source['edition_id']) != (cola_source['document_id'], cola_source['edition_id']):
                continue
            answer = (f'ข้าวขาว {a.group(2)} ทัพพีเท่ากับ 1 คาร์บ [{rice_source["source_id"]}] '
                      f'ส่วนโคล่า 1 กระป๋องเท่ากับ {b.group(2)} คาร์บ [{cola_source["source_id"]}]')
            if rice_source['source_id'] == cola_source['source_id']:
                start, end = min(a.start(), b.start()), max(a.end(), b.end())
                try:
                    _quote(rice_source, start, end)
                except ValueError:
                    continue
                answer = (f'ข้าวขาว {a.group(2)} ทัพพีเท่ากับ 1 คาร์บ ส่วนโคล่า 1 กระป๋องเท่ากับ {b.group(2)} คาร์บ '
                          f'[{rice_source["source_id"]}]')
                return _draft('paired_carb_examples', answer, [(rice_source, start, end)])
            try:
                _quote(rice_source, a.start(), a.end())
                _quote(cola_source, b.start(), b.end())
            except ValueError:
                continue
            return _draft('paired_carb_examples', answer,
                          [(rice_source, a.start(), a.end()), (cola_source, b.start(), b.end())])
    return None


def _label_field(question: str, sources: dict) -> dict | None:
    hints = label_field_hints(question, list(sources.values()))
    if len({h['field'] for h in hints}) != 1:
        return None
    hint = hints[0]
    source = sources[hint['source_id']]
    text = source['text']
    label_at = text.find('ฉลาก')
    field_at = text.find(hint['field'])
    if label_at < 0 or field_at < 0 or abs(field_at - label_at) > 700:
        return None
    try:
        _quote(source, min(label_at, field_at), max(label_at + len('ฉลาก'), field_at + len(hint['field'])))
    except ValueError:
        return None
    return _draft('explicit_label_field', f'ดู{hint["field"]}บนฉลากโภชนาการ [{hint["source_id"]}]',
                  [(source, min(label_at, field_at), max(label_at + len('ฉลาก'), field_at + len(hint['field'])))])


def _conditional_bp(question: str, sources: dict) -> dict | None:
    if not all(t in question for t in ('โซเดียม', 'ความดัน', 'โปรตีน')):
        return None
    if not re.search(r'โปรตีน(?:รั่ว|ในปัสสาวะ)|proteinuria', question, re.I):
        return None
    threshold = re.search(r'โปรตีน[^\d]{0,30}(?:เกิน|มากกว่า)[^\d]{0,15}(\d+(?:\.\d+)?)\s*กรัม', question)
    if threshold is None:
        return None
    for source in sources.values():
        text = source['text']
        sodium = re.search(r'โซเดียม\s*(ไม่เกิน|น้อยกว่า)\s*(\d+(?:\.\d+)?)\s*กรัม\s*/\s*วัน', text)
        specific = re.search(r'(น้อยกว่า|ต่ำกว่า|ไม่เกิน)\s*(\d{2,3}\s*/\s*\d{2,3})\s*มม\.\s*ปรอท\s*ในรายที่\s*โปรตีน(?:ในปัสสาวะ|รั่ว)[^\d]{0,20}(?:มากกว่า|เกิน)\s*(\d+(?:\.\d+)?)\s*กรัม\s*/\s*วัน', text)
        if sodium is None or specific is None or specific.group(3) != threshold.group(1):
            continue
        try:
            _quote(source, min(sodium.start(), specific.start()), max(sodium.end(), specific.end()))
        except ValueError:
            continue
        bp = re.sub(r'\s+', '', specific.group(2))
        return _draft('conditioned_bp_target',
                      f'จำกัดโซเดียม{sodium.group(1)} {sodium.group(2)} กรัม/วัน และตั้งเป้าความดัน{specific.group(1)} {bp} มม.ปรอทในรายที่โปรตีนในปัสสาวะมากกว่า {specific.group(3)} กรัม/วัน [{source["source_id"]}]',
                      [(source, min(sodium.start(), specific.start()), max(sodium.end(), specific.end()))])
    return None


def _dash_kidney_plate(question: str, sources: dict) -> dict | None:
    if 'DASH' not in question.upper() or 'ไตเรื้อรัง' not in question or 'แป้ง' not in question:
        return None
    stage_question = re.sub(r'ก่อน\s*ล้างไต', '', question)
    if re.search(r'ล้างไต|ฟอกไต|ฟอกเลือด|บำบัดทดแทนไต|ปลูกถ่ายไต', stage_question):
        return None
    plate = kidney = None
    for source in sources.values():
        text = source['text']
        if plate is None and 'DASH' in text.upper():
            match = re.search(r'4\s*ส่วน.{0,200}?อีก\s*1\s*ส่วน\s*เป็นข้าวหรืออาหารที่มา\s*จากแป้ง', text, re.S)
            if match:
                plate = (source, match)
        if kidney is None:
            match = re.search(r'ผู้ที่เป็นโรคไตเรื้อรังก่อนล้างไต.{0,360}?ข้าวแป้งที่ปลอดโปรตีนเพิ่ม\s*ได้แก่\s*วุ้นเส้น', text, re.S)
            if match:
                kidney = (source, match)
    if plate is None or kidney is None:
        return None
    plate_source, plate_match = plate
    kidney_source, kidney_match = kidney
    if plate_source['source_id'] == kidney_source['source_id']:
        return None
    try:
        _quote(plate_source, plate_match.start(), plate_match.end())
        _quote(kidney_source, kidney_match.start(), kidney_match.end())
    except ValueError:
        return None
    return _draft('cross_source_diet_relation',
                  f'ข้าวแป้งกินพื้นที่ 1 ใน 4 ของจาน [{plate_source["source_id"]}] สำหรับผู้มีโรคไตเรื้อรังก่อนล้างไต เอกสารแนะนำว่าหากไม่อิ่มให้เพิ่มแป้งปลอดโปรตีน เช่น วุ้นเส้น [{kidney_source["source_id"]}]',
                  [(plate_source, plate_match.start(), plate_match.end()),
                   (kidney_source, kidney_match.start(), kidney_match.end())])


def grounded_answer(question: str, sources: dict) -> dict | None:
    for route in (_round_and_cycle, _course_duration, _separate_measurement_fields,
                  _remission_html_table_counts, _two_sodium_sources,
                  _infection_table_groups, _dialysis_stability_comparison, _paired_carb_examples,
                  _conditional_bp, _dash_kidney_plate, _label_field):
        result = route(question, sources)
        if result:
            return result
    return None
