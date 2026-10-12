"""Run a locked extra-dev set through the already running local app.

Only the question is sent to /api/ask. Gold labels and reference answers are
joined locally after the response and stay under the ignored private folder.
The v26 run was initially unused; v28-v30 reuse its now-exposed qids.
None is an independent clinical test.
"""
from __future__ import annotations

import hashlib
import argparse
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx

ROOT = Path(__file__).resolve().parents[1]
SELECTION_SEED = "extra-dev-v25"  # Keep the original locked question set.
QUOTAS = {"number_unit": 7, "condition": 6, "fact": 6, "table": 5,
          "unanswerable": 4, "multi_page": 2}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(version="v26"):
    if version not in ("v26", "v28", "v29", "v30"):
        raise ValueError("Only locked v26, v28, v29 and v30 probes are supported")
    original_path = (ROOT / "reports/gemma_dev_plan.json" if version == "v30"
                     else ROOT / f"reports/history/{version}_gemma_dev_plan.json")
    original = read_json(original_path)
    if original["id"] != f"gemma-dev-{version}":
        raise ValueError("The extra probe is tied to the matching locked development plan")
    for name, digest in original["implementation_sha256"].items():
        if sha256(ROOT / "src/ncd_gemma" / name) != digest:
            raise ValueError(f"Implementation differs from the {version} lock: {name}")
    gold_path = ROOT / "data/gold/questions_all_reviewed.jsonl"
    if sha256(gold_path) != original["question_hash"]:
        raise ValueError("Gold differs from the locked plan")
    questions = [json.loads(line) for line in gold_path.read_text(encoding="utf-8").splitlines() if line]
    buckets = {kind: [] for kind in QUOTAS}
    for q in questions:
        if q["status"] == "gold" and q["split"] == "dev" and q["qid"] not in original["qids"]:
            if q["type"] in buckets:
                buckets[q["type"]].append(q)
    selected = []
    for kind, amount in QUOTAS.items():
        candidates = sorted(buckets[kind], key=lambda q: hashlib.sha256((SELECTION_SEED + ":" + q["qid"]).encode()).hexdigest())
        if len(candidates) < amount:
            raise ValueError(f"Not enough previously unused {kind} questions")
        selected.extend(candidates[:amount])
    plan = {"id": f"extra-dev-{version}",
            "scope": ("Previously unused questions from the same gold dev split; no tuning on these answers before the run"
                      if version == "v26" else f"Same extra-dev qids exposed in v26 and used for {version} development; regression only"),
            "selection": "type quotas and SHA256(extra-dev-v25:qid) order, preserved from the v25 extra plan", "quotas": QUOTAS,
            "qids": [q["qid"] for q in selected], "gold_sha256": original["question_hash"],
            "prompt_version": original["prompt_version"], "implementation_sha256": original["implementation_sha256"],
            "created_at_utc": datetime.now(timezone.utc).isoformat()}
    if version != "v26" and plan["qids"] != read_json(ROOT / "reports/extra_dev_v26_plan.json")["qids"]:
        raise ValueError("Regression must use exactly the 30 qids exposed in v26")
    path = ROOT / f"reports/extra_dev_{version}_plan.json"
    if path.exists():
        saved = read_json(path)
        for key in ("id", "selection", "quotas", "qids", "gold_sha256", "prompt_version", "implementation_sha256"):
            if saved[key] != plan[key]:
                raise ValueError("Existing extra-dev plan differs")
        plan = saved
    else:
        write_json(path, plan)
    return selected, plan


def run(version="v26"):
    selected, plan = prepare(version)
    output = ROOT / f"private/runs/extra-dev-{version}/answers.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    completed = {r["qid"]: r for line in output.read_text(encoding="utf-8").splitlines()
                 if line.strip() and (r := json.loads(line))} if output.exists() else {}
    if not set(completed) <= set(plan["qids"]):
        raise ValueError("Saved answers do not match locked qids")
    url = "http://127.0.0.1:8765"
    target = urlsplit(url)
    if target.scheme != "http" or target.hostname != "127.0.0.1" or target.port != 8765:
        raise ValueError("Only this local app may receive probe questions")
    with httpx.Client(base_url=url, timeout=180, trust_env=False) as client:
        for i, question in enumerate(selected, 1):
            if question["qid"] not in completed:
                for attempt in range(3):
                    response = client.post("/api/ask", json={"question": question["question"]})
                    if response.status_code != 429:
                        break
                    if attempt < 2:
                        time.sleep(3)
                if response.status_code not in (200, 502):
                    response.raise_for_status()
                prediction = response.json()
                if prediction.get("prompt_version") != plan["prompt_version"]:
                    raise ValueError("Local server version differs from locked probe")
                record = {"qid": question["qid"], "question": question["question"],
                          "prediction": prediction, "reference_answer": question["answer"],
                          "answerable": question["answerable"], "type": question["type"]}
                with output.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                completed[question["qid"]] = record
            print(json.dumps({"progress": f"{i}/{len(selected)}", "qid": question["qid"],
                              "status": completed[question["qid"]]["prediction"]["status"]}), flush=True)
    decisions = [r["prediction"]["status"] != "error" and
                 ((r["prediction"]["status"] == "answered") == r["answerable"])
                 for r in (completed[q["qid"]] for q in selected)]
    report = {"plan_id": plan["id"], "n": len(selected), "answerable": sum(q["answerable"] for q in selected),
              "status_counts": dict(Counter(completed[q["qid"]]["prediction"]["status"] for q in selected)),
              "decision_accuracy": round(sum(decisions) / len(decisions), 4),
              "false_abstentions": [q["qid"] for q in selected if q["answerable"] and completed[q["qid"]]["prediction"]["status"] != "answered"],
              "answered_unanswerable": [q["qid"] for q in selected if not q["answerable"] and completed[q["qid"]]["prediction"]["status"] == "answered"],
              "limitations": ["Remaining questions come from the same original gold dev split, not a new clinical dataset.",
                              f"{version} reused qids exposed in v26 and used for tuning; it is not an unseen evaluation." if version != "v26" else "v26 qids were unused before this run.",
                              "This is an extra local probe, not independent clinical validation.",
                              "Answer correctness requires manual evidence review; decision accuracy alone is insufficient."]}
    write_json(ROOT / f"reports/extra_dev_{version}_metrics.json", report)
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', choices=('v26','v28','v29','v30'), default='v30')
    run(parser.parse_args().version)
