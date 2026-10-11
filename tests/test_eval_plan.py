import json

import pytest

from ncd_gemma import evaluation


def test_plan_refuses_resume_after_implementation_identity_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(evaluation, "ROOT", tmp_path)
    gold = tmp_path / "data/gold/questions_all_reviewed.jsonl"
    gold.parent.mkdir(parents=True)
    gold.write_text(json.dumps({"qid": "synthetic-1", "status": "gold", "split": "dev", "type": "fact"}), encoding="utf-8")
    _, plan = evaluation.make_dev_plan(1)
    assert plan["implementation_sha256"]
    plan["implementation_sha256"]["verification.py"] = "changed"
    evaluation.write_json(tmp_path / "reports/gemma_dev_plan.json", plan)
    with pytest.raises(ValueError, match="Existing plan differs"):
        evaluation.make_dev_plan(1)
