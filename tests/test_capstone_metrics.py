import pytest
from ncd_gemma.capstone_eval.metrics import score_retrieval, score_answers, make_review_packet

def q(evidence):return dict(qid='q',question='?',answer='gold',answerable=True,evidence=evidence)
def unit(text='abc'):return dict(edition_id='e',pdf_page_start=1,pdf_page_end=1,text=text)
def test_two_evidence_one_covered_recall_half():
    gold=q([dict(edition_id='e',pdf_page=1,quote='abc'),dict(edition_id='e',pdf_page=2,quote='xyz')])
    m=score_retrieval([dict(qid='q',hits=[unit()])],[gold])
    assert m['recall@5']==.5
def test_wrong_edition_not_relevant():
    gold=q([dict(edition_id='other',pdf_page=1,quote='abc')])
    assert score_retrieval([dict(qid='q',hits=[unit()])],[gold])['recall@5']==0
def test_passage_not_parent_scored():
    gold=q([dict(edition_id='e',pdf_page=1,quote='abc')])
    assert score_retrieval([dict(qid='q',hits=[{**unit('zzz'),'parent_text':'abc'}])],[gold])['recall@5']==0
def test_error_kept_in_denominator():
    gold=[dict(q([]),qid=str(i)) for i in range(30)]
    rs=[dict(qid=str(i),prediction=dict(status='error' if i==0 else 'answered',citations=[],sources=[],answer='a')) for i in range(30)]
    assert score_answers(rs,gold)['error_rate']==1/30
def test_review_packet_hides_arm():
    rs=[dict(qid='q',arm='dense_default',prediction=dict(status='answered',answer='a',sources=[],citations=[]))]
    packet,key=make_review_packet(rs,[q([])])
    assert 'arm' not in packet[0] and key[0]['arm']=='dense_default'

def test_verification_failure_gets_no_abstention_credit():
    gold=[dict(q([]),answerable=False)]
    rs=[dict(qid='q',prediction=dict(status='insufficient_evidence',stop_reason='verification_unavailable',citations=[],sources=[]))]
    result=score_answers(rs,gold)
    assert result['error_rate']==1 and result['abstention_decision_accuracy']==0
