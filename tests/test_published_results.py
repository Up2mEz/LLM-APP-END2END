import importlib.util
from pathlib import Path
import shutil
import pytest

ROOT=Path(__file__).resolve().parents[1]

def load(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT/'scripts'))
    spec=importlib.util.spec_from_file_location('published_score_check',ROOT/'scripts/verify_published_results.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_saved_evidence_reproduces_published_results(monkeypatch):
    result=load(monkeypatch).verify()
    assert result['verified'] and result['model_calls']==0
    assert result['results']['capstone-current-v2']=={'dense_default':23,'hybrid_current':28}

def test_changed_archive_is_rejected_before_scoring(monkeypatch,tmp_path):
    module=load(monkeypatch)
    shutil.copytree(ROOT/'reports/published-evidence',tmp_path/'reports/published-evidence')
    archive=next((tmp_path/'reports/published-evidence').glob('*.gz'))
    archive.write_bytes(archive.read_bytes()+b'changed')
    monkeypatch.setattr(module,'ROOT',tmp_path)
    with pytest.raises(ValueError,match='Compressed evidence hash mismatch'):
        module.verify()
