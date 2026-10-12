"""Carry forward reviewed verdicts only for byte-identical v29/v30 outputs.

This is a regression receipt for exposed development questions, not a new
clinical or blinded review. Fail closed if any answer, status or citation moves.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def same_predictions(previous: Path, current: Path, qids: list[str]) -> list[dict]:
    old = read_rows(previous)
    new = read_rows(current)
    if [row["qid"] for row in old] != qids or [row["qid"] for row in new] != qids:
        raise ValueError("Run rows differ from the locked plan")
    for before, after in zip(old, new, strict=True):
        for field in ("question", "reference_answer", "answerable", "type"):
            if before.get(field) != after.get(field):
                raise ValueError(f"Question or gold changed: {after['qid']} {field}")
        for field in ("answer", "status", "citations"):
            if before["prediction"][field] != after["prediction"][field]:
                raise ValueError(f"Prediction changed: {after['qid']} {field}")
    return new


def main() -> None:
    plan = read_json(ROOT / "reports/gemma_dev_plan.json")
    old_plan = read_json(ROOT / "reports/history/v29_gemma_dev_plan.json")
    if plan["id"] != "gemma-dev-v30" or old_plan["id"] != "gemma-dev-v29":
        raise ValueError("Unexpected plan versions")
    if (plan["qids"], plan["question_hash"]) != (old_plan["qids"], old_plan["question_hash"]):
        raise ValueError("Original dev questions or gold changed")
    old_audit = read_json(ROOT / "reports/history/v29_semantic_audit.json")
    current_raw = ROOT / "private/runs/gemma-dev-v30/answers.jsonl"
    original = same_predictions(ROOT / "private/runs/gemma-dev-v29/answers.jsonl", current_raw, plan["qids"])
    if len(old_audit["core_matches"]) != 25 or old_audit["incorrect_or_incomplete"] or old_audit["false_abstentions"]:
        raise ValueError("Previous manual audit is not the expected baseline")
    audit = dict(old_audit)
    audit.update(current=plan["id"], baseline=old_plan["id"],
                 answers_sha256=hashlib.sha256(current_raw.read_bytes()).hexdigest(),
                 core_matches_v29=len(old_audit["core_matches"]),
                 improved_vs_v29=[], regressed_vs_v29=[], net_gain_vs_v29=0,
                 answer_changed_vs_v29=[],
                 new_api_calls_recorded=sum(r["prediction"]["stats"]["api_calls"] for r in original),
                 route_limitations="v30 adds negative-question guards around v29 evidence readers. Original 30 answer/status/citation tuples are identical to the reviewed v29 run; verdicts are inherited, not re-reviewed independently.")
    write_json(ROOT / "reports/semantic_audit.json", audit)

    extra_plan = read_json(ROOT / "reports/extra_dev_v30_plan.json")
    old_extra_plan = read_json(ROOT / "reports/extra_dev_v29_plan.json")
    if (extra_plan["qids"], extra_plan["gold_sha256"]) != (old_extra_plan["qids"], old_extra_plan["gold_sha256"]):
        raise ValueError("Extra-dev questions or gold changed")
    extra_raw = ROOT / "private/runs/extra-dev-v30/answers.jsonl"
    extra = same_predictions(ROOT / "private/runs/extra-dev-v29/answers.jsonl", extra_raw, extra_plan["qids"])
    previous = read_json(ROOT / "reports/extra_dev_v29_semantic_audit.json")
    if previous["strict_correct"] != 30 or len(previous["details"]) != 30:
        raise ValueError("Previous extra-dev audit is incomplete")
    extra_audit = dict(previous)
    extra_audit.update(plan_id=extra_plan["id"], comparison=old_extra_plan["id"],
                       raw_answers_sha256=hashlib.sha256(extra_raw.read_bytes()).hexdigest(),
                       strict_improved_qids=[], strict_regressed_qids=[], strict_net_gain=0,
                       changed_qids=[],
                       new_api_calls_recorded=sum(r["prediction"]["stats"]["api_calls"] for r in extra),
                       review_basis="Inherited coding-agent semantic verdicts only after all 30 answers, statuses and citations matched the reviewed v29 regression exactly. Exposed development sample, not blinded or clinical review.")
    write_json(ROOT / "reports/extra_dev_v30_semantic_audit.json", extra_audit)
    print(json.dumps({"original_qids_identical": len(original), "extra_qids_identical": len(extra),
                      "original_core_matches": len(audit["core_matches"]),
                      "extra_strict_correct": extra_audit["strict_correct"],
                      "new_api_calls_recorded": audit["new_api_calls_recorded"] + extra_audit["new_api_calls_recorded"]}))


if __name__ == "__main__":
    main()
