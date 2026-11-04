import importlib.util
from pathlib import Path
import pytest

def module():
    spec=importlib.util.spec_from_file_location('paired',Path(__file__).parents[1]/'scripts/paired_agent_eval.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def test_pair_validation_rejects_duplicate_and_unknown():
    m=module()
    r={'qid':'q1','arm':'old_v30','manifest_hash':'x'}
    assert m.validate([r],['q1'],'x')=={('q1','old_v30')}
    with pytest.raises(ValueError):m.validate([r,r],['q1'],'x')
    with pytest.raises(ValueError):m.validate([r],['q2'],'x')
    with pytest.raises(ValueError):m.validate([r],['q1'],'other')

def test_paired_order_and_guard():
    m=module()
    assert m.order(0)==['old_v30','current']
    assert m.order(1)==['current','old_v30']
    m.check_budget(119,1439,0,0)
    for args in [(120,0,0,0),(0,1440,0,0),(0,0,3,0),(0,0,0,14400)]:
        with pytest.raises(RuntimeError):m.check_budget(*args)

def test_deadline_and_durable_reservation(tmp_path,monkeypatch):
    m=module();calls=[]
    monkeypatch.setattr(m.os,'fsync',lambda fd:calls.append(fd))
    p=tmp_path/'deadline.json'
    assert m.deadline(p,100)==14500
    assert len(calls)>=1
    assert m.deadline(p,1000)==14500
    with pytest.raises(RuntimeError):m.require_time(14500,14400)
    r=tmp_path/'reservation.json';m.durable_json(r,{'request_id':'q1:old_v30','manifest_hash':'x'})
    with pytest.raises(RuntimeError):m.check_resume(r,[],'x')
    m.check_resume(r,[{'request_id':'q1:old_v30'}],'x')
    with pytest.raises(RuntimeError):m.check_resume(r,[{'request_id':'q1:old_v30'}],'wrong')

def test_stalled_worker_is_terminated():
    m=module()
    class Process:
        terminated=False
        def terminate(self):self.terminated=True
        def join(self,timeout):pass
        def is_alive(self):return not self.terminated
    class Pipe:
        def poll(self,seconds):return False
        def recv(self):raise AssertionError('Must not wait forever')
    p=Process()
    with pytest.raises(TimeoutError):m.receive_bounded(p,Pipe(),0.01)
    assert p.terminated

def test_real_durable_write(tmp_path):
    m=module();p=tmp_path/'record.json'
    m.durable_json(p,{'request_id':'one'})
    assert m.json.loads(p.read_text())=={'request_id':'one'}
