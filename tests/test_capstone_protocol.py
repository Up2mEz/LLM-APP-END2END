import json
from collections import Counter
from pathlib import Path
import pytest
from ncd_gemma.capstone_eval.protocol import select_questions, build_manifest, verify_manifest

def fixture_root(tmp_path):
    (tmp_path/'src/ncd_gemma').mkdir(parents=True)
    (tmp_path/'src/ncd_gemma/a.py').write_text('x=1')
    (tmp_path/'data/gold').mkdir(parents=True)
    qs=[dict(qid=f'q{j:03}',status='gold',split='dev',type=t,answerable=t!='unanswerable',question=f'Q{j}',answer='gold',evidence=[]) for j,t in enumerate(['condition','fact','multi_page','number_unit','table','unanswerable']*6)]
    (tmp_path/'data/gold/questions_all_reviewed.jsonl').write_text('\n'.join(json.dumps(q) for q in qs))
    return tmp_path

def test_selection_30_six_types(tmp_path):
    root=fixture_root(tmp_path); p=root/'data/gold/questions_all_reviewed.jsonl'
    q=select_questions(p)
    assert len(q)==30 and sum(x['answerable'] for x in q)==25
    assert set(Counter(x['type'] for x in q).values())=={5}
    assert q==select_questions(p)

def test_code_or_settings_drift_rejected(tmp_path):
    root=fixture_root(tmp_path); m=build_manifest(root,select_questions(root/'data/gold/questions_all_reviewed.jsonl'))
    verify_manifest(root,m)
    (root/'src/ncd_gemma/a.py').write_text('x=2')
    with pytest.raises(ValueError,match='drift'): verify_manifest(root,m)

def test_foreign_project_rejected(tmp_path):
    root=fixture_root(tmp_path); m=build_manifest(root,select_questions(root/'data/gold/questions_all_reviewed.jsonl'))
    m['project_id']='other'
    with pytest.raises(ValueError): verify_manifest(root,m)

def test_manifest_contains_no_credentials(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','secret-test-value')
    root=fixture_root(tmp_path); m=build_manifest(root,select_questions(root/'data/gold/questions_all_reviewed.jsonl'))
    assert 'secret-test-value' not in json.dumps(m)

def test_plan_refuses_overwrite(tmp_path,monkeypatch):
    from ncd_gemma.capstone_eval import __main__ as cli
    from ncd_gemma import config
    root=fixture_root(tmp_path)
    monkeypatch.setattr(config,'ROOT',root);monkeypatch.setattr(config,'load_environment',lambda:None)
    monkeypatch.setattr('sys.argv',['eval','plan'])
    cli.main()
    with pytest.raises(ValueError,match='overwrite'):cli.main()

def test_verify_makes_no_network_calls(tmp_path,monkeypatch):
    from ncd_gemma.capstone_eval import __main__ as cli
    from ncd_gemma import config
    import socket
    root=fixture_root(tmp_path)
    monkeypatch.setattr(config,'ROOT',root);monkeypatch.setattr(config,'load_environment',lambda:None)
    def forbidden(*args,**kwargs):raise AssertionError('Network forbidden')
    monkeypatch.setattr(socket,'socket',forbidden)
    monkeypatch.setattr('sys.argv',['eval','plan']);cli.main()
    monkeypatch.setattr('sys.argv',['eval','verify']);cli.main()
