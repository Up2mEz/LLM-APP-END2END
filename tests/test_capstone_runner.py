import pytest
from ncd_gemma.capstone_eval.runner import ArmRetriever, validate_records, Budget, service_failure, reserve_request, reconcile_reservation
from ncd_gemma.capstone_eval.protocol import RUN
from ncd_gemma.schemas import SearchArgs

def test_only_variant_differs():
    class Base:
        def search(self,args,variant):return [dict(query=args.query,variant=variant)]
    a,b=ArmRetriever(Base(),'A'),ArmRetriever(Base(),'B')
    assert a.search(SearchArgs(query='test'))==[dict(query='test',variant='A')]
    assert b.search(SearchArgs(query='test'))==[dict(query='test',variant='B')]
    assert a.calls[0]['args']==b.calls[0]['args']

def test_resume_rejects_foreign_or_duplicate_records():
    row=dict(run_id=RUN,manifest_hash='h',stage='answers',qid='q',arm='dense_default')
    with pytest.raises(ValueError):validate_records([row,row],'h','answers',['q'])
    with pytest.raises(ValueError):validate_records([{**row,'manifest_hash':'old'}],'h','answers',['q'])
    with pytest.raises(ValueError):validate_records([{**row,'stage':'pilot'}],'h','answers',['q'])

def test_outage_stops_at_three():
    b=Budget()
    for _ in range(3): b.record(1,True)
    with pytest.raises(RuntimeError,match='service'):b.check()

def test_budget_stops_without_extra_call():
    b=Budget();b.requests=62
    with pytest.raises(RuntimeError):b.check()

def test_http_path_uses_real_request_options(monkeypatch):
    from fastapi.testclient import TestClient
    from ncd_gemma import server,runtime_options
    class Fake:
        def run(self,question):
            assert question=='test question only'
            assert runtime_options.use_cache.get() is False
            assert runtime_options.use_reranker.get() is True
            return dict(status='answered',answer='test',sources=[],citations=[],stats={})
    monkeypatch.setattr(server,'_agent',Fake())
    monkeypatch.setenv('NCD_DEMO_PASSWORD','')
    with TestClient(server.app) as client:
        r=client.post('/api/ask',json=dict(question='test question only',use_cache=False,use_reranker=True))
    assert r.status_code==200
    assert r.json()['runtime_options']==dict(use_cache=False,use_reranker=True)
    assert runtime_options.use_cache.get() is True

def test_options_reset_on_error():
    from ncd_gemma.capstone_eval.runner import request_options
    from ncd_gemma import runtime_options
    with pytest.raises(RuntimeError):
        with request_options():
            assert runtime_options.use_cache.get() is False
            raise RuntimeError('fake failure')
    assert runtime_options.use_cache.get() is True

def test_verification_outage_counts_as_service_failure():
    p=dict(status='insufficient_evidence',stop_reason='verification_unavailable',trace=[])
    assert service_failure(p)
    b=Budget()
    for _ in range(3):b.record(1,service_failure(p))
    with pytest.raises(RuntimeError,match='service'):b.check()

def test_unresolved_reservation_blocks_retry(tmp_path):
    p=tmp_path/'reservation.json';b=Budget()
    reserve_request(p,b,'answers:q:A')
    with pytest.raises(RuntimeError,match='Unresolved'):reconcile_reservation(p,[],b)

def test_saved_reservation_reconciles_without_new_request(tmp_path):
    p=tmp_path/'reservation.json';b=Budget()
    reserve_request(p,b,'answers:q:A')
    r=dict(request_id='answers:q:A',prediction=dict(status='answered',stats=dict(api_calls=3)))
    reconcile_reservation(p,[r],b)
    assert b.requests==1 and b.attempts==3

def test_crash_after_budget_save_before_reservation_resolution(tmp_path,monkeypatch):
    from ncd_gemma.capstone_eval import runner
    p=tmp_path/'reservation.json';b=Budget();reserve_request(p,b,'answers:q:A')
    original=runner.write_json
    def interrupt(path,value):
        if path==p and value.get('resolved'):raise OSError('simulated interruption')
        original(path,value)
    r=dict(request_id='answers:q:A',prediction=dict(status='answered',stats=dict(api_calls=3)))
    monkeypatch.setattr(runner,'write_json',interrupt)
    with pytest.raises(OSError):reconcile_reservation(p,[r],b)
    monkeypatch.setattr(runner,'write_json',original)
    reconcile_reservation(p,[r],b)
    assert b.requests==1 and b.attempts==3
    reconcile_reservation(p,[r],b)
    assert b.requests==1 and b.attempts==3
