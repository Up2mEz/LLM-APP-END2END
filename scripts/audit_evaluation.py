"""Audit a versioned/v30 comparison without treating changed text as correct.

Changed predictions require explicit reviewed verdicts tied to their fingerprints.
Only identical answer/status/citations and cited sources inherit a v30 verdict.
Gold/reference answers remain local and never enter a model request.
"""
from __future__ import annotations

import hashlib
import json
import argparse
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "v32"
OUT = ROOT / "reports/evaluations" / VERSION
STRICT = {"correct", "correct_abstention"}
VERDICTS = STRICT | {"wrong", "partial", "false_abstention", "answered_unanswerable", "error", "service_unavailable"}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fingerprint(prediction):
    cited = {c["source_id"] for c in prediction["citations"]}
    value = {key: prediction[key] for key in ("answer", "status", "citations")}
    value["cited_sources"] = [s for s in prediction["sources"] if s["source_id"] in cited]
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def compare_suite(suite, overrides):
    plan = read(OUT / f"{suite}_plan.json")
    metrics = read(OUT / f"{suite}_metrics.json")
    old_plan_path = (ROOT / "reports/history/v30_gemma_dev_plan.json" if suite == "dev"
                     else ROOT / "reports/extra_dev_v30_plan.json")
    old_plan = read(old_plan_path)
    if plan["qids"] != old_plan["qids"] or plan["question_hash"] != old_plan.get("question_hash", old_plan.get("gold_sha256")):
        raise ValueError("Question selection or gold changed")
    new_path = ROOT / "private/runs" / plan["id"] / "answers.jsonl"
    old_path = ROOT / "private/runs" / old_plan["id"] / "answers.jsonl"
    old, new = rows(old_path), rows(new_path)
    if [r["qid"] for r in old] != plan["qids"] or [r["qid"] for r in new] != plan["qids"]:
        raise ValueError("Comparison requires two complete ordered runs")
    if metrics["answers_sha256"] != sha(new_path):
        raise ValueError("Metrics do not describe these predictions")
    old_audit = read(ROOT / ("reports/history/v30_semantic_audit.json" if suite == "dev"
                            else "reports/extra_dev_v30_semantic_audit.json"))
    if suite == "dev":
        previous = {}
        for qid in old_plan["qids"]:
            if qid in old_audit["core_matches"]:
                verdict = "correct"
            elif qid in old_audit["label_correct_abstentions"]:
                verdict = "correct_abstention"
            else:
                raise ValueError("Unexpected v30 baseline verdict; inspect explicitly")
            previous[qid] = {"verdict": verdict, "note": old_audit["notes"][qid]}
    else:
        previous = {d["qid"]: d for d in old_audit["details"]}
    expected_old_hash = old_audit.get("answers_sha256", old_audit.get("raw_answers_sha256"))
    if expected_old_hash != sha(old_path):
        raise ValueError("Baseline raw outputs no longer match their semantic audit")
    details, changed, review_queue = [], [], []
    for before, after in zip(old, new, strict=True):
        qid, prediction = after["qid"], after["prediction"]
        for field in ("question", "reference_answer", "answerable"):
            if before[field] != after[field]:
                raise ValueError(f"Question/gold changed: {qid} {field}")
        digest = fingerprint(prediction)
        identical = digest == fingerprint(before["prediction"])
        if not identical:
            changed.append(qid)
            review_queue.append({"qid": qid, "suite": suite, "prediction_sha256": digest,
                                 "question": after["question"], "reference_answer": after["reference_answer"],
                                 "answer": prediction["answer"], "status": prediction["status"],
                                 "previous_answer": before["prediction"]["answer"],
                                 "citations": prediction["citations"],
                                 "cited_sources": [s for s in prediction["sources"] if s["source_id"] in
                                                   {c["source_id"] for c in prediction["citations"]}]})
            review = overrides.get(qid)
            if not review or review.get("prediction_sha256") != digest:
                continue
            verdict, note = review["verdict"], review["note"]
        else:
            verdict, note = previous[qid]["verdict"], previous[qid]["note"]
        if verdict not in VERDICTS or not note.strip():
            raise ValueError(f"Invalid review: {qid}")
        status = prediction["status"]
        if (verdict in {"correct", "wrong", "partial", "answered_unanswerable"}) != (status == "answered"):
            raise ValueError(f"Verdict/status mismatch: {qid}")
        if verdict == "error" and status != "error":
            raise ValueError(f"Error verdict/status mismatch: {qid}")
        if verdict == "service_unavailable" and not any(
                e.get("event") in {"proxy_error", "verification_error"} for e in prediction["trace"]):
            raise ValueError(f"No service-failure evidence: {qid}")
        details.append({"qid": qid, "answerable": after["answerable"], "type": after["type"],
                        "status": status, "verdict": verdict, "note": note,
                        "prediction_sha256": digest, "inherited_identical_v30": identical,
                        "cited_documents": sorted({c["document_id"] for c in prediction["citations"]})})
    write(ROOT / f"private/runs/{plan['id']}/review_queue.json", review_queue)
    if len(details) != len(new):
        missing = [r["qid"] for r in new if r["qid"] not in {d["qid"] for d in details}]
        return None, missing
    counts = Counter(d["verdict"] for d in details)
    improved = [d["qid"] for d in details if d["verdict"] in STRICT and previous[d["qid"]]["verdict"] not in STRICT]
    regressed = [d["qid"] for d in details if d["verdict"] not in STRICT and previous[d["qid"]]["verdict"] in STRICT]
    audit = {
        "plan_id": plan["id"], "current": plan["id"], "baseline": old_plan["id"], "comparison": old_plan["id"],
        "n": len(details), "answerable_denominator": sum(d["answerable"] for d in details),
        "answers_sha256": sha(new_path), "raw_answers_sha256": sha(new_path), "baseline_answers_sha256": sha(old_path),
        "verdict_counts": dict(counts), "strict_correct": sum(counts[k] for k in STRICT),
        "strict_correct_rate": round(sum(counts[k] for k in STRICT) / len(details), 4),
        "core_matches": [d["qid"] for d in details if d["verdict"] == "correct"],
        "label_correct_abstentions": [d["qid"] for d in details if d["verdict"] == "correct_abstention"],
        "incorrect_or_incomplete": [d["qid"] for d in details if d["verdict"] in {"wrong", "partial", "answered_unanswerable", "error"}],
        "false_abstentions": [d["qid"] for d in details if d["verdict"] == "false_abstention"],
        "service_unavailable_qids": [d["qid"] for d in details if d["verdict"] == "service_unavailable"],
        "partial_or_needs_context_review": [],
        "strict_improved_qids": improved, "strict_regressed_qids": regressed,
        "strict_net_gain": len(improved) - len(regressed), "changed_qids": changed,
        "new_api_calls_recorded": metrics["new_api_calls_recorded"],
        "review_basis": "Coding-agent review of changed outputs against unchanged gold and cited source text. Identical outputs inherit the v30 verdict only after fingerprint checks. Exposed regression; not blinded expert or clinical review.",
        "details": details,
    }
    write(OUT / f"{suite}_semantic_audit.json", audit)
    return audit, []


def main():
    global VERSION, OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default=VERSION)
    args = parser.parse_args()
    if not re.fullmatch(r"v[1-9][0-9]*", args.version):
        raise ValueError("Invalid version")
    VERSION = args.version
    OUT = ROOT / "reports/evaluations" / VERSION
    review_path = OUT / "reviewed_changes.json"
    overrides = read(review_path) if review_path.exists() else {}
    audits, pending = {}, {}
    for suite in ("dev", "extra"):
        audits[suite], pending[suite] = compare_suite(suite, overrides)
    if any(pending.values()):
        print(json.dumps({"needs_review": pending}))
        raise SystemExit(1)
    plans = {suite: read(OUT / f"{suite}_plan.json") for suite in audits}
    old_plan = read(ROOT / "reports/history/v30_gemma_dev_plan.json")
    report = {
        "baseline": "v30", "current": VERSION, "scope": "Same 60 exposed dev questions; fresh-cache operational regression, not an isolated model-quality experiment.",
        "gold_sha256": plans["dev"]["question_hash"], "same_ordered_qids": True,
        "runtime_changes_vs_v30_lock": [k for k, v in old_plan["implementation_sha256"].items()
                                       if plans["dev"]["implementation_sha256"][k] != v],
        "added_locking": ["runtime and evaluation code", "all released data files", "retrieval configs and schemas",
                         "reused retrieval Python code", "runtime settings", "cache mode", "resume plan identity"],
        "results": {suite: {"v30_strict_correct": 30, f"{VERSION}_strict_correct": a["strict_correct"],
                            "core_correct_answerable": len(a["core_matches"]),
                            "correct_abstentions": len(a["label_correct_abstentions"]),
                            "changed_qids": a["changed_qids"], "regressed_qids": a["strict_regressed_qids"],
                            "improved_qids": a["strict_improved_qids"], "net_gain": a["strict_net_gain"],
                            "service_unavailable_qids": a["service_unavailable_qids"],
                            "semantic_failure_qids": a["incorrect_or_incomplete"] + a["false_abstentions"],
                            "metrics": read(OUT / f"{suite}_metrics.json")} for suite, a in audits.items()},
        "new_api_calls_recorded": sum(a["new_api_calls_recorded"] for a in audits.values()),
        "v30_new_api_calls_recorded": 0,
        "limitations": ["v30 used cached older model responses; provider variation and fresh timing are not controlled.",
                        "Both development sets were previously used for tuning; no claim about unseen clinical accuracy.",
                        "Semantic verdicts are coding-agent assessments, not independent expert labels."],
    }
    v31_path = ROOT / "reports/evaluations/v31/dev_plan.json"
    if VERSION != "v31" and v31_path.exists():
        previous = read(v31_path)
        report["same_code_and_settings_as_v31"] = all(previous[k] == plans["dev"][k] for k in
            ("implementation_sha256", "reused_implementation_sha256", "configuration_sha256",
             "data_sha256", "settings", "prompt_sha256", "cache_mode"))
    write(OUT / "comparison.json", report)
    print(json.dumps({"results": {s: a["verdict_counts"] for s, a in audits.items()},
                      "new_api_calls": report["new_api_calls_recorded"]}))


if __name__ == "__main__":
    main()
