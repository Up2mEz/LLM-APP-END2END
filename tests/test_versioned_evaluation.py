import json
from types import SimpleNamespace

import pytest

from ncd_gemma import versioned_evaluation as ev


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setattr(ev, "ROOT", tmp_path)
    monkeypatch.setattr(ev, "_data_hashes", lambda: {})
    gold = tmp_path / "data/gold/questions_all_reviewed.jsonl"
    gold.parent.mkdir(parents=True)
    q = {"qid": "synthetic-1", "status": "gold", "split": "dev", "type": "fact",
         "question": "Synthetic question", "answer": "Private gold answer", "answerable": True, "evidence": []}
    gold.write_text(json.dumps(q), encoding="utf-8")
    tables = tmp_path / "data/table_context/tables.jsonl"
    tables.parent.mkdir()
    tables.write_text("{}")
    baseline = tmp_path / "reports/history/v30_gemma_dev_plan.json"
    ev.write_json(baseline, {"id": "gemma-dev-v30", "qids": [q["qid"]], "question_hash": ev.file_hash(gold)})
    return tmp_path, q, baseline


def test_new_version_keeps_baseline_and_refuses_code_drift(project, monkeypatch):
    root, _, baseline = project
    old = baseline.read_bytes()
    _, plan = ev.make_plan(1)
    assert baseline.read_bytes() == old
    assert ev.make_plan(1)[1] == plan
    real_hash = ev.file_hash
    monkeypatch.setattr(ev, "file_hash", lambda p: "changed" if p.name == "llm.py" else real_hash(p))
    with pytest.raises(ValueError, match="implementation_sha256"):
        ev.make_plan(1)
    assert baseline.read_bytes() == old
    assert ev.make_plan(1, "v32")[1]["id"] == "gemma-dev-v32"


def test_settings_and_cache_policy_are_immutable(project, monkeypatch):
    ev.make_plan(1)
    with pytest.raises(ValueError, match="cache_mode"):
        ev.make_plan(1, cache_mode="shared")
    monkeypatch.setenv("NCD_REQUEST_TIMEOUT", "89")
    with pytest.raises(ValueError, match="settings"):
        ev.make_plan(1)


def test_gold_drift_and_old_version_are_rejected(project):
    root, _, _ = project
    with pytest.raises(ValueError, match="historical"):
        ev.make_plan(1, "v30")
    with pytest.raises(ValueError, match="Version"):
        ev.make_plan(1, "../../escape")
    gold = root / "data/gold/questions_all_reviewed.jsonl"
    gold.write_text(gold.read_text() + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Gold differs"):
        ev.make_plan(1)


def test_resume_checks_identity_and_sends_question_only(project):
    root, q, _ = project
    selected, plan = ev.make_plan(1)
    seen = []

    def run(question):
        seen.append(question)
        return {"prompt_version": plan["prompt_version"], "status": "insufficient_evidence",
                "stop_reason": "completed", "answer": "", "sources": [], "citations": [],
                "stats": {"api_calls": 0, "model_rounds": 0, "reported_tokens_including_cache": 0, "elapsed_ms": 1}}

    agent = SimpleNamespace(settings=ev.evaluation_settings(plan), run=run)
    first = ev.run_locked(agent, selected, plan)
    assert seen == [q["question"]]
    assert ev.run_locked(agent, selected, plan) == first
    assert len(seen) == 1
    answers = root / f"private/runs/{plan['id']}/answers.jsonl"
    record = json.loads(answers.read_text())
    record["plan_sha256"] = "foreign-plan"
    answers.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="Saved answer identity"):
        ev.run_locked(agent, selected, plan)


def test_isolated_run_rejects_prepopulated_cache(project):
    _, _, _ = project
    selected, plan = ev.make_plan(1)
    settings = ev.evaluation_settings(plan)
    settings.cache_dir.mkdir(parents=True)
    (settings.cache_dir / "old.json").write_text("{}")
    with pytest.raises(ValueError, match="empty cache"):
        ev.run_locked(SimpleNamespace(settings=settings), selected, plan)


def test_data_release_hash_guard_checks_content(project, monkeypatch):
    root, _, _ = project
    monkeypatch.undo()
    monkeypatch.setattr(ev, "ROOT", root)
    path = root / "data/table_context/tables.jsonl"
    ev.write_json(root / "provenance/public_data_release.json",
                  {"files": [{"path": "data/table_context/tables.jsonl", "sha256": ev.file_hash(path)}]})
    assert ev._data_hashes()
    path.write_text("modified")
    with pytest.raises(ValueError, match="Data differs"):
        ev._data_hashes()
