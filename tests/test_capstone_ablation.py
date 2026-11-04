import importlib.util
import json
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('ablation',Path(__file__).resolve().parents[1]/'scripts/capstone_reranker_ablation.py')
ablation=importlib.util.module_from_spec(spec);spec.loader.exec_module(ablation)

def test_ablation_keeps_query_and_disables_cache_reranker(tmp_path,monkeypatch):
    from ncd_gemma import runtime_options,retrieval
    source=tmp_path/'reports'/ablation.SOURCE;source.mkdir(parents=True)
    raw=tmp_path/'private'/ablation.SOURCE;raw.mkdir(parents=True)
    manifest={'identity':'fixture'}
    (source/'manifest.json').write_text(json.dumps(manifest))
    qs=[dict(qid=str(i),question=f'Question {i}',answerable=True,evidence=[dict(edition_id='e',pdf_page=1,quote='abc')]) for i in range(30)]
    (source/'questions.jsonl').write_text('\n'.join(json.dumps(q) for q in qs))
    on=[dict(run_id=ablation.SOURCE,manifest_hash=ablation.json_hash(manifest),arm='hybrid_current',qid=q['qid'],hits=[],elapsed_seconds=2) for q in qs]
    (raw/'retrieval.jsonl').write_text('\n'.join(json.dumps(r) for r in on))
    calls=[]
    class FakeRetriever:
        def search(self,args,variant):
            assert runtime_options.use_cache.get() is False
            assert runtime_options.use_reranker.get() is False
            assert variant=='B' and args.top_k==5
            calls.append(args.query)
            return []
    monkeypatch.setattr(ablation,'ROOT',tmp_path)
    monkeypatch.setattr(ablation,'load_environment',lambda:None)
    monkeypatch.setattr(ablation,'verify_manifest',lambda *a,**k:None)
    monkeypatch.setattr(retrieval,'EvidenceRetriever',FakeRetriever)
    ablation.main()
    assert calls==[q['question'] for q in qs]
    assert runtime_options.use_cache.get() is True and runtime_options.use_reranker.get() is True
    result=json.loads((tmp_path/'reports'/ablation.RUN/'metrics.json').read_text())
    assert result['n']==30 and result['complete'] and result['reranker_off']['recall@5']==0
    with pytest.raises(ValueError,match='existing'):ablation.main()
    assert len(calls)==30
