import json
import pytest

from ncd_gemma.agent import parse_answer
from ncd_gemma.evidence import evidence_spans, span_range, TableContext
from ncd_gemma.verification import parse_review


def test_passage_selection_copies_exact_text_and_rejects_unknown_id():
    source = {'text': 'ตัวอย่างหลักฐานบรรทัดหนึ่ง\nข้อความยืนยันที่ตามมา'}
    raw = {'status':'answered', 'answer':'คำตอบตัวอย่าง [S1]',
           'citations':[{'source_id':'S1','span_ids':['P1']}]}
    assert parse_answer(json.dumps(raw), {'S1':source}, True).citations[0].quote == source['text']
    raw['citations'][0]['span_ids'] = ['P99']
    with pytest.raises(ValueError):
        parse_answer(json.dumps(raw), {'S1':source}, True)


def test_every_passage_reconstructs_a_bounded_source_range():
    source = {'text': '\n'.join(['ข้อความตัวอย่าง '*12 for _ in range(20)])}
    for span in evidence_spans(source):
        start,end=span_range(source,[span['span_id']])
        assert '\n'.join(source['text'].splitlines()[start-1:end]) == span['text']
    with pytest.raises(ValueError):
        span_range(source, ['P1',evidence_spans(source)[-1]['span_id']])


def test_short_focused_window_keeps_label_value_and_condition_in_one_passage():
    source={'text':'ข้อมูลประกอบ '*65+'\nจำนวนผู้เข้าร่วมกิจกรรม\n18 คน เฉพาะกลุ่มที่ลงทะเบียนไว้ก่อนเริ่มงาน'}
    spans=evidence_spans(source)
    assert len(spans)==1 and '18 คน' in spans[0]['text']


def test_text_table_headers_route_to_row_reasoning_without_pdf_cells():
    from ncd_gemma.evidence import table_answer_route
    assert table_answer_route({'text':'ข้อมูลทั่วไป จำนวน (คน) ร้อยละ\nกลุ่ม A 18 60.0'})
    assert table_answer_route({'text':'ชนิดของยา ขนาดยาที่แนะนำ ผลของยา\nข้อมูลสังเคราะห์ A'})
    assert not table_answer_route({'text':'บทความอธิบายโครงการ มีผู้ร่วมงานจำนวนมากจากหลายพื้นที่'})


def test_passage_reviewer_cannot_pass_a_requirement_absent_from_answer():
    sources={'S1':{'text':'ตัวอย่างหลักฐาน กิจกรรม A เหมาะกับกลุ่ม B'}}
    review={'supported':True,'reason':'ตัวอย่างตรวจ','checks':[
        {'requirement':'ชื่อกิจกรรม','covered':True,'answer_quote':'กิจกรรม A',
         'source_id':'S1','span_ids':['P1']} ]}
    assert parse_review({'content':json.dumps(review)}, 'กิจกรรม A [S1]', sources).supported
    with pytest.raises(ValueError, match='verbatim'):
        parse_review({'content':json.dumps(review)}, 'มีหลายกิจกรรม [S1]', sources)


def test_non_table_boundary_context_keeps_next_recommendation_and_edition():
    def c(id,page,text,edition='e1'):
        return {'chunk_id':id,'document_id':'synthetic','edition_id':edition,
                'pdf_page_start':page,'pdf_page_end':page,'char_start':page*100,'text':text}
    parent=c('a',2,'ข้อความที่จบก่อนข้อแนะนำสำคัญ')
    continuation=c('b',3,'ข้อแนะนำต่อเนื่องในเอกสารเดียวกัน')
    other=c('c',3,'ข้อความคนละฉบับห้ามรวม','e2')
    result=TableContext([parent,continuation,other]).enrich(parent)
    assert continuation['text'] in result['text'] and other['text'] not in result['text']
    assert parent['text']=='ข้อความที่จบก่อนข้อแนะนำสำคัญ'


def test_previous_comparator_survives_neighbor_expansion():
    def c(cid, page, text):
        return {'chunk_id':cid,'document_id':'same','edition_id':'e1',
                'pdf_page_start':page,'pdf_page_end':page,'char_start':page*100,'text':text}
    previous = c('previous', 1, 'Conventional intermittent เหมาะกับไหลเวียนคงที่\n' + 'บริบท ' * 175)
    current = c('current', 2, 'SLED เหมาะกับผู้ป่วยความดันค่อนข้างต่ำ')
    result = TableContext([previous, current]).enrich(current)
    assert 'Conventional intermittent' in result['text'] and 'SLED' in result['text']
