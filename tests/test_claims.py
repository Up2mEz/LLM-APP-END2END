import json
import pytest
from ncd_gemma.claims import render_claims, reviewed_claims, prune_invalid_claims, repair_verbatim_legacy_citation
from ncd_gemma.verification import parse_review
from ncd_gemma.agent import parse_answer

SOURCES = {'S1': {'text':'หลักฐานสังเคราะห์: ประเด็นแรกคือข้อมูล A\nคำแนะนำอื่นที่ผู้ใช้ไม่ได้ถาม'}}

def payload():
    return {'status':'answered','claims':[{'text':'ประเด็นแรกคือข้อมูล A','source_id':'S1','span_ids':['P1']}]}

def test_claim_renderer_binds_real_source_and_adds_marker():
    draft=parse_answer(json.dumps(payload()),SOURCES,True)
    assert draft.answer=='ประเด็นแรกคือข้อมูล A [S1]'
    assert draft.citations[0].quote==SOURCES['S1']['text']


def test_claim_cannot_insert_an_unsupported_translation_or_change_a_value():
    raw=payload();raw['claims'][0]['text']='ประเด็นแรกคือข้อมูล A (invented translation)'
    with pytest.raises(ValueError,match='exact excerpt'):render_claims(raw,SOURCES)


def test_invalid_redundant_claim_is_dropped_but_no_fact_is_created():
    raw = {'status':'answered','claims':[
        {'text':'ประเด็นแรกคือข้อมูล B','source_id':'S1','span_ids':['P1']},
        {'text':'ประเด็นแรกคือข้อมูล A','source_id':'S1','span_ids':['P1']}]}
    pruned = prune_invalid_claims(raw, SOURCES)
    assert len(pruned['claims']) == 1
    assert render_claims(pruned, SOURCES)['answer'] == 'ประเด็นแรกคือข้อมูล A [S1]'
    assert len(raw['claims']) == 2
    all_bad = {'status':'answered','claims':[raw['claims'][0], raw['claims'][0]]}
    assert prune_invalid_claims(all_bad, SOURCES) == all_bad


def test_legacy_line_recovery_requires_whole_verbatim_answer_and_named_source():
    sources = {'S1': {'text': 'หัวข้อ\nสำหรับประเทศญี่ปุ่นมีการตรวจโปรตีนในปัสสาวะกลุ่มเ ด็กและกลุ่มวัยทำงาน มาตั้งแต่ช่วง ค.ศ. 1970s'}}
    candidate = {'status':'answered',
                 'answer':'สำหรับประเทศญี่ปุ่นมีการตรวจโปรตีนในปัสสาวะกลุ่มเด็กและกลุ่มวัยทำงานมาตั้งแต่ช่วง ค.ศ. 1970s [S1]',
                 'citations':[{'source_id':'S1','start_line':37,'end_line':37}]}
    fixed = repair_verbatim_legacy_citation(candidate, sources)
    assert fixed['citations'][0]['start_line'] == 2
    assert 'กลุ่มเ ด็ก' in fixed['answer']
    assert parse_answer(json.dumps(fixed), sources, True).status == 'answered'
    assert candidate['citations'][0]['start_line'] == 37
    invented = {**candidate, 'answer':'ข้อความที่เอกสารไม่ได้กล่าว [S1]'}
    assert repair_verbatim_legacy_citation(invented, sources) == invented

@pytest.mark.parametrize('field,value', [('source_id','S99'),('span_ids',['P99']),('text','ปลอม marker [S2]')])
def test_claim_renderer_rejects_fabricated_source_and_marker(field,value):
    raw=payload();raw['claims'][0][field]=value
    with pytest.raises(ValueError):render_claims(raw,SOURCES)

def test_unreviewed_extra_advice_is_not_released():
    answer='ประเด็นแรกคือข้อมูล A [S1] คำแนะนำอื่นที่ผู้ใช้ไม่ได้ถาม [S1]'
    raw={'checks':[{'requirement':'ประเด็นแรก','covered':True,'answer_quote':'ประเด็นแรกคือข้อมูล A',
                   'source_id':'S1','span_ids':['P1']}], 'supported':True,'reason':''}
    review=parse_review({'content':json.dumps(raw)},answer,SOURCES)
    result=reviewed_claims(review,SOURCES)
    assert result['answer']=='ประเด็นแรกคือข้อมูล A [S1]'
    assert 'คำแนะนำอื่น' not in result['answer']

def test_empty_review_reason_does_not_replace_evidence_checks():
    raw={'checks':[{'requirement':'ประเด็นแรก','covered':True,'answer_quote':'ข้อความที่ไม่มี',
                   'source_id':'S1','span_ids':['P1']}], 'supported':True,'reason':''}
    with pytest.raises(ValueError): parse_review({'content':json.dumps(raw)},'ประเด็นแรกคือข้อมูล A',SOURCES)


def test_review_claim_id_retains_complete_condition_instead_of_a_number_fragment():
    claims={'C1':{'text':'สำหรับกลุ่ม B มีจำนวน 12 คน','source_id':'S1','span_ids':['P1']}}
    raw={'checks':[{'requirement':'จำนวนในกลุ่ม B','covered':True,'claim_id':'C1',
                   'source_id':'S1','span_ids':['P1']}], 'supported':True,'reason':''}
    review=parse_review({'content':json.dumps(raw)},'สำหรับกลุ่ม B มีจำนวน 12 คน [S1]',SOURCES,claims)
    assert reviewed_claims(review,SOURCES)['answer']=='สำหรับกลุ่ม B มีจำนวน 12 คน [S1]'
    raw['checks'][0]['claim_id']='C9'
    with pytest.raises(ValueError):parse_review({'content':json.dumps(raw)},'สำหรับกลุ่ม B มีจำนวน 12 คน [S1]',SOURCES,claims)


def test_format_binding_never_invents_a_source_or_edits_the_answer():
    from ncd_gemma.claims import bind_existing_markers
    raw={'status':'answered','answer':'คำตอบ [S1]'}
    fixed=bind_existing_markers(raw,SOURCES)
    assert fixed['answer']==raw['answer'] and fixed['citations'][0]['quote']==SOURCES['S1']['text']
    invalid={'status':'answered','answer':'คำตอบ [S99]'}
    assert bind_existing_markers(invalid,SOURCES)==invalid
    no_id={'status':'answered','answer':'คำตอบไม่มีแหล่งอ้างอิง'}
    assert bind_existing_markers(no_id,SOURCES)==no_id
