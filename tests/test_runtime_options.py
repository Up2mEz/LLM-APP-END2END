from types import SimpleNamespace
from threading import Lock
from fastapi.testclient import TestClient
from ncd_gemma import runtime_options as options, server
from ncd_gemma.config import Settings
from ncd_gemma.llm import ProxyClient
from ncd_gemma.passage_rerank import PassageReranker
from ncd_gemma.retrieval import EvidenceRetriever
from ncd_gemma.schemas import SearchArgs


def test_no_cache_bypasses_existing_and_never_writes(tmp_path):
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=str(len(calls)), tool_calls=[]), finish_reason='stop')], usage=None)
    client = ProxyClient.__new__(ProxyClient)
    client.settings = Settings(cache_dir=tmp_path)
    client.endpoint_identity = 'test'
    client.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    args = ([{'role':'user','content':'same question'}], [], 'none', 20)
    client.complete(*args)
    before = {p.name:p.read_bytes() for p in tmp_path.iterdir()}
    token = options.use_cache.set(False)
    try:
        assert not client.complete(*args)['cached']
        assert not client.complete(*args)['cached']
        client.complete([{'role':'user','content':'new question'}], [], 'none', 20)
    finally:
        options.use_cache.reset(token)
    assert before == {p.name:p.read_bytes() for p in tmp_path.iterdir()}
    assert len(calls) == 4
    assert client.complete(*args)['cached']


def test_reranker_cache_disabled_recomputes_without_writes(tmp_path):
    calls = []
    ranker = PassageReranker.__new__(PassageReranker)
    ranker.cache = tmp_path
    def predict(pairs, **kwargs):
        calls.append(pairs)
        return [1., 2.]
    ranker.model = SimpleNamespace(predict=predict)
    evidence = [{'text':'one'}, {'text':'two'}]
    ranker.rank('question', evidence)
    before = {p.name:p.read_bytes() for p in tmp_path.iterdir()}
    token = options.use_cache.set(False)
    try:
        ranker.rank('question', evidence)
        ranker.rank('question', evidence)
    finally:
        options.use_cache.reset(token)
    assert len(calls) == 3
    assert before == {p.name:p.read_bytes() for p in tmp_path.iterdir()}


def test_disabled_reranker_is_never_called():
    r = EvidenceRetriever.__new__(EvidenceRetriever)
    r.allowed = {}; r.lock = Lock()
    hit = {'chunk_id':'c','document_id':'d','edition_id':'e','text':'text'}
    r.raw = SimpleNamespace(search=lambda *a, **k: [hit])
    r.table_context = SimpleNamespace(enrich=lambda x:x)
    r.focus = SimpleNamespace(select=lambda x,q:[x])
    def fail(*args):
        raise AssertionError('reranker called')
    r.passage_reranker = SimpleNamespace(rank=fail)
    token = options.use_reranker.set(False)
    try:
        assert r.search(SearchArgs(query='test')) == [hit]
    finally:
        options.use_reranker.reset(token)


def test_request_options_are_isolated_and_reset_on_failure(monkeypatch):
    monkeypatch.setenv('NCD_DEMO_PASSWORD','')
    seen = []
    def run(question):
        seen.append((options.use_cache.get(), options.use_reranker.get()))
        if question == 'fail': raise RuntimeError('test')
        return {'status':'answered'}
    monkeypatch.setattr(server,'get_agent',lambda:SimpleNamespace(run=run))
    client = TestClient(server.app, raise_server_exceptions=False)
    response = client.post('/api/ask',json={'question':'test','use_cache':False,'use_reranker':False})
    assert response.json()['runtime_options'] == {'use_cache':False,'use_reranker':False}
    assert client.post('/api/ask',json={'question':'fail','use_cache':False,'use_reranker':False}).status_code == 500
    client.post('/api/ask',json={'question':'default'})
    assert seen == [(False,False),(False,False),(True,True)]
    assert options.use_cache.get() and options.use_reranker.get()
