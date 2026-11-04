import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('judge',Path(__file__).resolve().parents[1]/'scripts/capstone_judge.py')
judge=importlib.util.module_from_spec(spec)
spec.loader.exec_module(judge)

def row(i='x',verdict='correct'):
    return dict(item_id=i,verdict=verdict,reason='supported',evidence_refs=['S1'])

def test_incomplete_or_duplicate_judgment_rejected():
    with pytest.raises(ValueError):judge.validate([row()],['x','y'])
    with pytest.raises(ValueError):judge.validate([row(),row()],['x'])
    with pytest.raises(ValueError):judge.validate([row(verdict='probably')],['x'])

def test_service_failure_cannot_receive_judge_success():
    packet=[dict(item_id='x',service_failure=True)]
    key=[dict(item_id='x',arm='dense_default',qid='q')]
    result=judge.aggregate([row(verdict='correct_abstention')],packet,key)
    assert result['dense_default']['successes']==0
    assert result['dense_default']['verdict_counts']=={'service_error':1}

def test_uncertain_is_kept_in_denominator():
    packet=[dict(item_id=i,service_failure=False) for i in ['x','y']]
    key=[dict(item_id=i,arm='dense_default',qid=i) for i in ['x','y']]
    result=judge.aggregate([row(),row('y','uncertain')],packet,key)
    assert result['dense_default']['n']==2
    assert result['dense_default']['semantic_success']==0.5

def test_corrupt_rationale_encoding_rejected():
    with pytest.raises(ValueError,match='encoding'):
        judge.validate([{**row(),'reason':'service failure ?????'}],['x'])
